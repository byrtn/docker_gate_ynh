"""
Docker Gate — module de gestion Docker + YunoHost.

Étape 2 (11/07/2026) : logique réelle de création/suppression d'apps Docker
exposées derrière YunoHost, dans les deux modes (chemin et sous-domaine dédié).

Principe de sécurité (voir manifest.toml + conf/docker_gate.sudoers) :
ce module tourne avec un utilisateur système restreint. Les seules commandes
privilégiées (yunohost app install/remove, domain add/cert install) passent
par `sudo -n`, autorisées de façon ciblée par le fichier sudoers posé à
l'installation — jamais de sudo générique.

Internationalisation (15/07/2026) : tous les messages utilisateur (erreurs,
avertissements) passent par `i18n.t(key, lang, **kwargs)` — `lang` est un
paramètre explicite de chaque fonction plutôt qu'un contexte Flask implicite,
pour que ce module reste testable indépendamment de Flask et pour gérer
correctement le cas d'une création lancée en tâche de fond (thread séparé de
la requête HTTP d'origine, voir app.py) : la langue de l'utilisateur est
capturée avant le lancement du thread, jamais déduite après coup.
"""
import json
import os
import re
import shlex
import subprocess
import tempfile
import time
from pathlib import Path

import docker
import requests
import yaml

from i18n import t

DATA_FILE = Path(__file__).parent / "data" / "apps.json"
PORT_RANGE_START = 9100
PORT_RANGE_END = 9999

# Logo appliqué sur chaque conteneur exposé via "redirect" (chantier 1,
# 16/07/2026) — mêmes 2 mécanismes YunoHost que pour Docker Gate lui-même
# (voir scripts/install), appliqués ici sur l'instance "redirect" créée.
CHILD_LOGO_SOURCE = Path(__file__).parent / "static" / "docker-gate-app-logo.png"

docker_client = docker.from_env()


class DockerConnectorError(Exception):
    """Erreur métier lisible, affichée telle quelle à l'utilisateur."""


def _load_state():
    """Audit chantier 5 (17/07/2026, cas limites) : avant ce correctif, un
    `data/apps.json` corrompu (écriture interrompue par un disque plein, un
    crash, ou une édition manuelle ratée) faisait planter TOUTE l'interface
    (chaque route appelle cette fonction). Un fichier illisible est
    maintenant mis de côté (jamais supprimé — conservé pour investigation/
    récupération manuelle) et remplacé par un état vide, pour que l'app
    reste utilisable plutôt que totalement indisponible."""
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        corrupted_path = DATA_FILE.with_name(f"{DATA_FILE.name}.corrupted-{int(time.time())}")
        try:
            DATA_FILE.rename(corrupted_path)
        except OSError:
            pass
        return []


def _save_state(apps):
    """Écriture atomique (audit chantier 5, 17/07/2026) : écrit dans un
    fichier temporaire puis `os.replace()` (renommage atomique sur un même
    système de fichiers) plutôt que d'écrire directement dans `apps.json` —
    une interruption en cours d'écriture (crash, disque plein) ne peut plus
    laisser un fichier à moitié écrit et donc invalide pour `_load_state()`."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=DATA_FILE.parent, prefix=".apps-", suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(apps, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, DATA_FILE)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def list_apps(lang="en"):
    apps = _load_state()
    # Rétrocompatibilité (audit 17/07/2026) : les apps créées avant le
    # passage au modèle à 3 groupes n'ont qu'un booléen "public" en état
    # disque — déduit ici à la lecture, jamais réécrit, comportement réel
    # inchangé pour ces apps existantes.
    for a in apps:
        if "visibility" not in a:
            a["visibility"] = "visitors" if a.get("public") else "admins"

    # Réconciliation avec l'état réel YunoHost (bug trouvé le 18/07/2026) :
    # si une app enfant est supprimée directement depuis le panneau
    # d'administration YunoHost (en contournant Docker Gate), notre fichier
    # d'état ne le sait jamais tout seul et continuait de l'afficher comme
    # fonctionnelle alors que sa permission SSO/conf nginx n'existe plus.
    # Vérifié à chaque affichage : toute entrée dont le yunohost_app_id ne
    # correspond plus à une app YunoHost réelle est retirée de l'état — le
    # conteneur Docker restant (le cas échéant) redevient détectable comme
    # résidu via /audit, qui sait déjà le gérer proprement. Aucune donnée
    # n'est perdue ici : seul le suivi devenu faux est corrigé, la
    # suppression réelle du conteneur/volume reste soumise aux mêmes
    # garde-fous que d'habitude (page Audit & nettoyage).
    try:
        real_ids = {
            a["id"]
            for a in json.loads(
                _run_sudo(["yunohost", "app", "list", "--output-as", "json"], t("err_list_apps", lang), lang)
            )["apps"]
        }
        still_valid = [a for a in apps if not a.get("yunohost_app_id") or a["yunohost_app_id"] in real_ids]
        if len(still_valid) != len(apps):
            apps = still_valid
            _save_state(apps)
    except (DockerConnectorError, ValueError, KeyError):
        # Best-effort : si la vérification échoue (sudo, JSON invalide...),
        # on affiche l'état tel quel plutôt que de casser la page d'accueil.
        pass

    return apps


def _slug_is_valid(slug):
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{1,30}", slug))


def _slug_already_used(slug):
    return any(a["slug"] == slug for a in _load_state())


def _pick_free_port(lang):
    """Choisit un port libre dans la plage 9100-9999, en vérifiant à la fois
    notre fichier d'état ET les ports réellement utilisés par Docker (pour ne
    jamais entrer en collision avec une app installée manuellement, comme
    Portainer sur 9101)."""
    used = {a["host_port"] for a in _load_state()}

    for container in docker_client.containers.list(all=True):
        for bindings in (container.ports or {}).values():
            if not bindings:
                continue
            for b in bindings:
                try:
                    used.add(int(b["HostPort"]))
                except (KeyError, ValueError, TypeError):
                    continue

    for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
        if port not in used:
            return port

    raise DockerConnectorError(t("err_no_free_port", lang))


def _run_sudo(args, error_message, lang):
    """Exécute une commande sudo -n (non-interactive), autorisée par le
    fichier sudoers scellé. Lève DockerConnectorError avec un message lisible
    en cas d'échec, plutôt que de laisser fuiter une trace brute à l'écran."""
    result = subprocess.run(
        ["/usr/bin/sudo", "-n"] + args,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise DockerConnectorError(
            t("err_sudo_detail", lang, message=error_message, detail=result.stderr.strip() or result.stdout.strip())
        )
    return result.stdout


def existing_domains(lang):
    """Liste les domaines déjà connus de YunoHost (pour peupler le menu
    déroulant du mode 'chemin')."""
    output = _run_sudo(
        ["yunohost", "domain", "list", "--output-as", "json"],
        t("err_list_domains", lang),
        lang,
    )
    data = json.loads(output)
    return data.get("domains", [])


def fetch_compose_from_url(url, lang):
    """Récupère le contenu d'un docker-compose.yml depuis une URL fournie
    par l'utilisateur (ex: lien GitHub brut). Restreint à https:// — cette
    app a déjà des droits élevés sur le serveur (sudo ciblé), donc le risque
    marginal d'une requête sortante n'ajoute rien de nouveau, mais on refuse
    quand même http:// en clair par hygiène de base."""
    if not url.startswith("https://"):
        raise DockerConnectorError(t("err_https_only", lang))
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise DockerConnectorError(t("err_fetch_url", lang, error=e))
    if len(response.content) > 200_000:
        raise DockerConnectorError(t("err_file_too_large", lang))
    return response.text


def inspect_docker_image(image_name, lang):
    """Télécharge (si besoin) et inspecte une image Docker pour deviner
    automatiquement son port et son volume par défaut, quand l'utilisateur
    ne donne qu'un nom d'image (le cas le moins informatif des trois formats
    acceptés). Best-effort : beaucoup d'images ne déclarent pas ces
    informations dans leurs métadonnées (seulement dans leur documentation
    en texte libre) — dans ce cas on ne remplit que ce qu'on a pu trouver,
    jamais de valeur inventée."""
    try:
        image = docker_client.images.pull(image_name)
    except docker.errors.APIError as e:
        raise DockerConnectorError(t("err_pull_image", lang, image=image_name, error=e))

    config = image.attrs.get("Config", {}) or {}
    result = {"image": image_name, "container_port": None, "data_path": None, "suggested_slug": None}

    exposed_ports = config.get("ExposedPorts") or {}
    if exposed_ports:
        # Format Docker : {"80/tcp": {}, "443/tcp": {}} — on prend le premier.
        first_port = next(iter(exposed_ports))
        result["container_port"] = first_port.split("/")[0]

    volumes = config.get("Volumes") or {}
    if volumes:
        # Format Docker : {"/data": {}} — on prend le premier déclaré.
        result["data_path"] = next(iter(volumes))

    return result


def parse_docker_run_command(text, lang):
    """Parse une commande `docker run ...` (celle qu'on trouve typiquement
    sur Docker Hub/GitHub) et en extrait image/port/données/variables —
    sans passer par un docker-compose.yml. Gère les commandes étalées sur
    plusieurs lignes avec des '\\' de continuation (format habituel des
    tutoriels). Philosophie changée le 13/07/2026 à la demande de Patrick :
    l'utilisateur donne UNE SEULE entrée brute (image, commande docker run,
    ou docker-compose.yml), jamais une liste de champs à remplir à la main."""
    # Rejoint les lignes coupées par '\' en fin de ligne (continuation shell).
    joined = re.sub(r"\\\s*\n", " ", text)
    joined = joined.replace("\n", " ").strip()
    if not joined.startswith("docker "):
        raise DockerConnectorError(t("err_not_docker_run", lang))

    try:
        tokens = shlex.split(joined)
    except ValueError as e:
        raise DockerConnectorError(t("err_parse_command", lang, error=e))

    if "run" not in tokens:
        raise DockerConnectorError(t("err_no_docker_run", lang))

    tokens = tokens[tokens.index("run") + 1:]

    result = {"image": None, "container_port": None, "data_path": None, "env_vars": None, "url_env_var": None, "suggested_slug": None}
    env_pairs = []
    i = 0
    image = None
    while i < len(tokens):
        tok = tokens[i]
        if tok == "--name" and i + 1 < len(tokens):
            result["suggested_slug"] = tokens[i + 1]
            i += 2
            continue
        if tok in ("-p", "--publish") and i + 1 < len(tokens):
            result["container_port"] = tokens[i + 1].split(":")[-1]
            i += 2
            continue
        if tok in ("-v", "--volume") and i + 1 < len(tokens):
            parts = tokens[i + 1].split(":")
            if len(parts) >= 2 and not parts[0].startswith("/"):
                # Volume nommé (rare en ligne de commande, mais possible).
                result["data_path"] = parts[1]
            elif len(parts) >= 2:
                # Montage d'un chemin hôte (le cas le plus courant en CLI,
                # ex: -v /vw-data/:/data/) — on veut quand même le chemin
                # À L'INTÉRIEUR du conteneur, donc la partie après le ':'.
                result["data_path"] = parts[1]
            i += 2
            continue
        if tok in ("-e", "--env") and i + 1 < len(tokens):
            k, _, v = tokens[i + 1].partition("=")
            env_pairs.append((k.strip(), v.strip()))
            i += 2
            continue
        if tok.startswith("-"):
            # Option non reconnue (--name, --restart, -d...) : on l'ignore,
            # avec son éventuel argument s'il n'est pas collé (ex: --name X).
            # Heuristique simple : si le token suivant ne commence pas par
            # '-' et n'est pas l'image (dernier token), on le saute aussi.
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-") and i + 1 != len(tokens) - 1:
                i += 2
            else:
                i += 1
            continue
        # Ce qui reste est l'image (dernier token positionnel).
        image = tok
        i += 1

    if image:
        result["image"] = image

    other_lines = []
    for key, value in env_pairs:
        if not result["url_env_var"] and re.match(r"^https?://", value):
            result["url_env_var"] = key
        else:
            other_lines.append(f"{key}={value}")
    if other_lines:
        result["env_vars"] = "\n".join(other_lines)

    if not result["image"]:
        raise DockerConnectorError(t("err_no_image_in_command", lang))

    return result


def smart_parse_input(text, lang):
    """Point d'entrée unique : détecte automatiquement ce que l'utilisateur
    a collé — une commande 'docker run', un docker-compose.yml, ou juste un
    nom d'image — et appelle le bon analyseur. Philosophie "zero-formulaire"
    actée le 13/07/2026 : une seule case à remplir, pas trois formats
    différents à choisir soi-même."""
    stripped = text.strip()
    if not stripped:
        raise DockerConnectorError(t("err_nothing_to_analyze", lang))

    if stripped.startswith("docker "):
        return parse_docker_run_command(stripped, lang)

    # Un docker-compose.yml contient presque toujours au moins un retour à
    # la ligne et une structure "services:" ou "image:". Un simple nom
    # d'image, lui, tient sur une seule ligne sans ':' suivi d'espace.
    if "\n" in stripped or stripped.lstrip().startswith(("services:", "image:")):
        return parse_compose_snippet(stripped, lang)

    # Sinon : probablement juste un nom d'image (ex: "vaultwarden/server:latest").
    if re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._/-]*(:[a-zA-Z0-9._-]+)?", stripped):
        return inspect_docker_image(stripped, lang)

    raise DockerConnectorError(t("err_unrecognized_format", lang))


def parse_compose_snippet(text, lang):
    """Extrait image/port/données d'un extrait docker-compose.yml collé par
    l'utilisateur — beaucoup de projets self-hosted en publient un tout prêt
    (contrairement au reste de leur doc, souvent en texte libre, ce format
    est structuré et fiable à lire automatiquement).

    Accepte aussi bien un fichier complet (avec une clé `services:`) qu'un
    simple extrait du bloc d'un seul service. Ne remplit QUE ce qu'il trouve
    — à l'utilisateur de compléter le reste si besoin, pas d'invention de
    valeurs par défaut hasardeuses (règle #1 : jamais d'affirmation qui ne
    soit pas vérifiée)."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise DockerConnectorError(t("err_invalid_compose", lang, error=e))

    if not isinstance(data, dict):
        raise DockerConnectorError(t("err_invalid_compose_notdict", lang))

    if "services" in data and isinstance(data["services"], dict):
        services = data["services"]
        if not services:
            raise DockerConnectorError(t("err_no_service_found", lang))
        service_key, service = next(iter(services.items()))
    else:
        # Peut-être un simple extrait (juste le bloc d'un service, sans la
        # clé "services:" englobante).
        service = data
        service_key = None

    if not isinstance(service, dict):
        raise DockerConnectorError(t("err_unrecognized_service_format", lang))

    result = {"image": None, "container_port": None, "data_path": None, "env_vars": None, "url_env_var": None,
              "suggested_slug": service.get("container_name") or service_key}

    if "image" in service:
        result["image"] = str(service["image"])

    ports = service.get("ports")
    if ports and isinstance(ports, list) and ports:
        first = str(ports[0])
        # Formats possibles : "3001", "3001:3001", "127.0.0.1:3001:3001"
        result["container_port"] = first.split(":")[-1]

    volumes = service.get("volumes")
    if volumes and isinstance(volumes, list):
        for v in volumes:
            v_str = str(v)
            parts = v_str.split(":")
            if len(parts) < 2:
                continue
            source = parts[0]
            # On ignore les montages spéciaux de l'hôte (chemin absolu en
            # source, ex: /var/run/docker.sock) — ce ne sont pas des volumes
            # de données classiques, juste prendre "le premier trouvé" donnait
            # de mauvais résultats sur de vrais fichiers (ex: Portainer,
            # dont le premier volume est le socket Docker, pas les données).
            if source.startswith("/"):
                continue
            result["data_path"] = parts[1]
            break

    environment = service.get("environment")
    if environment:
        # Le format docker-compose accepte deux syntaxes équivalentes :
        # une liste ["CLE=valeur", ...] ou un dictionnaire {CLE: valeur}.
        pairs = []
        if isinstance(environment, list):
            for e in environment:
                k, _, v = str(e).partition("=")
                pairs.append((k.strip(), v.strip()))
        elif isinstance(environment, dict):
            pairs = [(str(k), str(v)) for k, v in environment.items()]

        # On repère une éventuelle variable "d'URL de base" (valeur qui
        # ressemble à une adresse web, ex: DOMAIN=https://vw.domain.tld) —
        # cette variable-là n'a pas besoin d'être recopiée telle quelle : sa
        # vraie valeur sera calculée automatiquement à partir du domaine et
        # du chemin choisis dans le formulaire (simplification demandée par
        # Patrick le 13/07/2026, pour éviter une double saisie manuelle).
        other_lines = []
        for key, value in pairs:
            if not result["url_env_var"] and re.match(r"^https?://", value):
                result["url_env_var"] = key
            else:
                other_lines.append(f"{key}={value}")
        if other_lines:
            result["env_vars"] = "\n".join(other_lines)

    if not result["image"] and not result["container_port"] and not result["data_path"] and not result["env_vars"]:
        raise DockerConnectorError(t("err_nothing_extracted", lang))

    return result


def parse_env_vars_text(text, lang):
    """Parse un texte au format 'CLE=valeur' (une par ligne, comme un fichier
    .env) en dictionnaire. Ignore les lignes vides et les commentaires
    (lignes commençant par #). Lève une erreur claire si une ligne non-vide
    ne contient pas de '=' (règle #1 : jamais d'échec silencieux — mieux
    vaut prévenir l'utilisateur qu'ignorer silencieusement une ligne mal
    formée qui pourrait être importante pour l'app)."""
    env = {}
    for i, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise DockerConnectorError(t("err_invalid_env_line", lang, line_no=i, line=line))
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def build_create_steps(mode, has_data):
    """Construit la liste ordonnée des CLÉS d'étapes prévues pour une
    création, selon le mode et si des données persistantes sont demandées.
    Utilisée à la fois pour préparer l'affichage de la progression ET par
    create_docker_app pour signaler son avancement réel — les deux ne
    peuvent donc jamais être désynchronisés.

    Retourne des clés stables (i18n.STRINGS), jamais du texte affichable
    directement — la traduction se fait à l'affichage (progress.html),
    jamais ici (ces clés doivent rester indépendantes de la langue de
    l'utilisateur, y compris pour matcher le job de progression, voir
    progress.py)."""
    steps = ["step_check_params", "step_pick_port"]
    if mode == "subdomain":
        steps += [
            "step_create_domain",
            "step_dns_diag",
            "step_web_diag",
            "step_get_cert",
            "step_check_cert",
        ]
    if has_data:
        steps.append("step_create_volume")
    steps += ["step_run_container", "step_expose_app"]
    return steps


def check_subdomain_status(new_subdomain, domain_parent, lang):
    """Vérifie l'état d'un sous-domaine potentiel AVANT toute tentative de
    création, pour donner un retour clair et non-bloquant à l'utilisateur
    (demande de Patrick, 13/07/2026) plutôt que de découvrir le problème
    après coup via une erreur YunoHost.

    Retourne un dict avec "status" valant :
    - "free" : n'existe pas, création possible
    - "exists_empty" : existe déjà mais sans app installée dessus — peut
      être réutilisé tel quel (cas d'un essai précédent interrompu, ex:
      certificat qui avait échoué)
    - "exists_used" : existe déjà AVEC une app dessus — jamais réutilisable,
      proposer un nom alternatif plutôt que de bloquer sans solution
    """
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", new_subdomain or ""):
        return {"status": "invalid"}

    target_domain = f"{new_subdomain}.{domain_parent}"
    domains = existing_domains(lang)

    if target_domain not in domains:
        return {"status": "free", "domain": target_domain}

    try:
        info_raw = _run_sudo(
            ["yunohost", "domain", "info", target_domain, "--output-as", "json"],
            t("err_verify_domain", lang, domain=target_domain),
            lang,
        )
        info = json.loads(info_raw)
        apps_on_domain = info.get("apps", [])
    except DockerConnectorError:
        # Prudence : si on n'arrive pas à vérifier, on considère occupé
        # plutôt que de risquer d'écraser quelque chose (règle #1).
        apps_on_domain = ["?"]

    if apps_on_domain:
        suggestion = f"{new_subdomain}-2"
        return {"status": "exists_used", "domain": target_domain, "suggestion": suggestion}

    return {"status": "exists_empty", "domain": target_domain}


def check_path_status(domain, path, lang):
    """Vérifie si domain+path est déjà occupé par une app YunoHost existante,
    AVANT la tentative de création — même logique préventive que
    check_subdomain_status pour le mode "sous-domaine dédié" (parité UX,
    15/07/2026 : le mode "chemin" n'avait jusqu'ici aucun contrôle
    équivalent, l'échec ne remontait qu'à l'étape finale d'exposition)."""
    normalized_path = path if path.startswith("/") else f"/{path}"
    if not re.fullmatch(r"/[a-zA-Z0-9._~-]*(?:/[a-zA-Z0-9._~-]+)*", normalized_path):
        return {"status": "invalid"}

    apps_raw = _run_sudo(
        ["yunohost", "app", "list", "--output-as", "json"],
        t("err_list_apps", lang),
        lang,
    )
    apps = json.loads(apps_raw)["apps"]
    target = f"{domain}{normalized_path}".rstrip("/")

    for a in apps:
        existing = (a.get("domain_path") or "").rstrip("/")
        if existing == target:
            return {"status": "used", "domain": domain, "path": normalized_path, "app_name": a.get("name")}

    return {"status": "free", "domain": domain, "path": normalized_path}


def create_docker_app(slug, image, container_port, mode, domain, domain_parent, path, new_subdomain, visibility, lang, data_path="", env_vars=None, url_env_var="", reuse_existing_domain=False, on_step=None):
    """Point d'entrée principal de la création d'une app Docker exposée.

    mode: "path" ou "subdomain"
    - path      : expose sur {domain}{path}
    - subdomain : crée {new_subdomain}.{domain_parent}, expose à la racine

    domain_parent est un champ DISTINCT de domain (deux menus déroulants
    séparés dans le formulaire, un par mode) — ne jamais les confondre,
    incident déjà rencontré et corrigé le 12/07/2026.

    lang : langue de l'utilisateur ayant lancé la création, capturée dans la
    requête HTTP d'origine (voir app.py) — la création tourne dans un thread
    séparé, sans accès direct au contexte Flask/session, d'où ce paramètre
    explicite plutôt qu'une déduction implicite (15/07/2026, i18n).

    data_path (optionnel) : chemin À L'INTÉRIEUR du conteneur où l'app range
    ses données persistantes (ex: "/app/data" pour Uptime Kuma — voir la
    documentation de l'app sur Docker Hub). Si fourni, un volume Docker
    nommé et dédié est créé et monté à cet endroit, pour que les données
    survivent à un redémarrage ou une recréation du conteneur.

    on_step (optionnel) : fonction appelée avec la CLÉ de chaque étape au
    moment où elle démarre (voir build_create_steps et progress.py) —
    permet à l'interface d'afficher une progression détaillée pendant les
    opérations longues (téléchargement d'image, certificat Let's Encrypt).

    env_vars (optionnel) : dictionnaire de variables d'environnement à
    passer au conteneur.

    url_env_var (optionnel) : nom d'une variable d'environnement à calculer
    et injecter AUTOMATIQUEMENT avec l'adresse complète de l'app une fois
    connue (ex: "DOMAIN", "ROOT_URL" — le nom exact dépend de l'app, voir sa
    documentation). Évite d'avoir à taper soi-même une URL qui doit rester
    synchronisée avec le domaine/chemin choisis par ailleurs — simplification
    demandée par Patrick le 13/07/2026, suite à un premier essai jugé trop
    manuel/source d'erreur.

    reuse_existing_domain (optionnel, mode sous-domaine uniquement) : si
    True, ne tente PAS de créer le domaine YunoHost (il existe déjà et a été
    vérifié vide via check_subdomain_status) — évite une erreur YunoHost sur
    un domaine déjà déclaré. Sert aussi de mécanisme de reprise naturel :
    si le certificat échoue lors d'un premier essai, le domaine reste créé ;
    relancer l'installation avec ce paramètre reprend juste après, sans tout
    recommencer.

    Lève DockerConnectorError avec un message clair à chaque étape qui peut
    échouer de façon réellement bloquante (paramètres invalides, port
    indisponible, Docker qui refuse de lancer le conteneur...), pour que
    l'utilisateur comprenne ce qui a coincé (règle #1 : jamais d'échec
    silencieux).

    Décision du 14/07/2026 (Patrick, suite à l'anomalie #49) : en mode
    "subdomain", un DNS pas encore propagé chez le registrar ne doit PLUS
    bloquer toute l'installation (diagnostic DNS/Web en échec, certificat
    Let's Encrypt inobtenable) — l'app est quand même exposée avec le
    certificat disponible (même auto-signé), et un avertissement est
    consigné dans `entry["warnings"]` plutôt que de tout annuler. Point
    vérifié (règle #1, 14/07/2026) : le cron quotidien YunoHost
    (`yunohost domain cert renew`) ne fait que renouveler un certificat
    Let's Encrypt déjà en place et proche d'expirer — il ne bascule JAMAIS
    tout seul un domaine resté sur un certificat auto-signé vers Let's
    Encrypt. Une fois le DNS propagé, il faut donc relancer l'installation
    (le sous-domaine existant sera détecté et réutilisé via
    `reuse_existing_domain`), pas simplement attendre.
    """
    warnings = []

    def step(key):
        if on_step:
            on_step(key)

    step("step_check_params")
    if not _slug_is_valid(slug):
        raise DockerConnectorError(t("err_invalid_slug", lang))
    if _slug_already_used(slug):
        raise DockerConnectorError(t("err_slug_already_used", lang, slug=slug))

    try:
        container_port = int(container_port)
    except (TypeError, ValueError):
        raise DockerConnectorError(t("err_port_not_a_number", lang))

    step("step_pick_port")
    host_port = _pick_free_port(lang)

    # --- Résolution du domaine/chemin cible selon le mode ---
    if mode == "subdomain":
        if not new_subdomain or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", new_subdomain):
            raise DockerConnectorError(t("err_invalid_subdomain", lang))
        target_domain = f"{new_subdomain}.{domain_parent}"
        target_path = "/"

        if reuse_existing_domain:
            # Le sous-domaine existe déjà et a été vérifié vide (voir
            # check_subdomain_status) — on ne le recrée pas, YunoHost
            # refuserait de toute façon un domaine déjà déclaré.
            pass
        else:
            step("step_create_domain")
            _run_sudo(
                ["yunohost", "domain", "add", target_domain],
                t("err_create_subdomain", lang, domain=target_domain),
                lang,
            )

        # Un diagnostic doit exister avant de pouvoir demander un certificat
        # (leçon apprise le 10/07/2026, incident Portainer). Leurs résultats
        # sont vérifiés, mais depuis le 14/07/2026 un échec ici n'annule plus
        # l'installation (décision Patrick, anomalie #49) : c'est le signe le
        # plus courant d'une zone DNS pas encore paramétrée chez le
        # registrar — on avertit au lieu de bloquer, l'app sera de toute
        # façon exposée avec le certificat disponible (voir plus bas).
        step("step_dns_diag")
        dns_diag = subprocess.run(
            ["/usr/bin/sudo", "-n", "yunohost", "diagnosis", "run", "--force", "--", "dnsrecords"],
            capture_output=True, text=True, timeout=120,
        )
        if dns_diag.returncode != 0:
            warnings.append(t("warn_dns_diag_failed", lang, domain=target_domain))

        step("step_web_diag")
        web_diag = subprocess.run(
            ["/usr/bin/sudo", "-n", "yunohost", "diagnosis", "run", "--force", "--", "web"],
            capture_output=True, text=True, timeout=120,
        )
        if web_diag.returncode != 0:
            warnings.append(t("warn_web_diag_failed", lang, domain=target_domain))

        step("step_get_cert")
        cert_install = subprocess.run(
            ["/usr/bin/sudo", "-n", "yunohost", "domain", "cert", "install", target_domain],
            capture_output=True, text=True, timeout=180,
        )
        if cert_install.returncode != 0:
            warnings.append(t("warn_cert_not_obtained", lang, domain=target_domain))

        # yunohost domain cert install peut renvoyer un code de sortie 0 sans
        # avoir réellement installé de certificat Let's Encrypt (bug YunoHost :
        # continue silencieux quand le domaine n'est pas encore prêt pour ACME —
        # découvert le 13/07/2026 sur test1.wappos.fr, DNS absent chez OVH).
        # On vérifie donc le résultat réel plutôt que le seul code de retour.
        step("step_check_cert")
        try:
            cert_check_output = _run_sudo(
                ["yunohost", "domain", "cert", "status", target_domain, "--output-as", "json"],
                t("err_verify_cert_status", lang, domain=target_domain),
                lang,
            )
            json_start = cert_check_output.index("{")
            json_end = cert_check_output.rindex("}") + 1
            cert_data = json.loads(cert_check_output[json_start:json_end])
            ca_type = cert_data["certificates"][target_domain]["CA_type"]
        except (DockerConnectorError, ValueError, KeyError, json.JSONDecodeError) as e:
            warnings.append(t("warn_verify_cert_failed", lang, domain=target_domain, error=e))
            ca_type = None

        if ca_type and ca_type != "letsencrypt":
            warnings.append(t("warn_cert_not_letsencrypt", lang, domain=target_domain, ca_type=ca_type))
    else:
        target_domain = domain
        target_path = path if path.startswith("/") else f"/{path}"

    # --- Variable d'URL de base calculée automatiquement (optionnel) ---
    # Le chemin ("/") ne doit pas être doublé en fin d'URL (ex: éviter
    # "https://x.fr/vaultwarden-test/" en mode sous-domaine où target_path
    # vaut déjà "/").
    if url_env_var:
        env_vars = dict(env_vars) if env_vars else {}
        if target_path == "/":
            env_vars[url_env_var] = f"https://{target_domain}/"
        else:
            env_vars[url_env_var] = f"https://{target_domain}{target_path}"

    # --- Volume de données persistantes (optionnel) ---
    volume_name = None
    if data_path:
        step("step_create_volume")
        volume_name = f"docker-gate-{slug}-data"
        try:
            docker_client.volumes.create(name=volume_name)
        except docker.errors.APIError as e:
            raise DockerConnectorError(t("err_create_volume", lang, error=e))

    # --- Lancement du conteneur Docker ---
    step("step_run_container")
    container_name = f"docker-gate-{slug}"
    run_kwargs = dict(
        name=container_name,
        detach=True,
        restart_policy={"Name": "always"},
        ports={f"{container_port}/tcp": ("127.0.0.1", host_port)},
    )
    if env_vars:
        run_kwargs["environment"] = env_vars
    if volume_name:
        run_kwargs["volumes"] = {volume_name: {"bind": data_path, "mode": "rw"}}

    try:
        docker_client.containers.run(image, **run_kwargs)
    except docker.errors.APIError as e:
        # Audit chantier 5 (17/07/2026) : le volume a pu être créé juste
        # au-dessus (data_path renseigné) — avant ce correctif, un échec ICI
        # laissait ce volume orphelin sans aucune tentative de nettoyage,
        # alors que le même volume est nettoyé plus bas si c'est l'étape
        # d'exposition qui échoue à la place. Incohérence corrigée : même
        # geste défensif qu'à l'exposition, pour un échec sur cette étape.
        if volume_name:
            try:
                docker_client.volumes.get(volume_name).remove()
            except docker.errors.NotFound:
                pass
        raise DockerConnectorError(t("err_run_container", lang, error=e))

    # --- Exposition via l'app officielle "redirect" ---
    step("step_expose_app")
    # Passthrough direct sur le vocabulaire natif YunoHost (admins/all_users/
    # visitors) — audit 17/07/2026, docs/02-wappos/audits/2026-07-17-audit-permissions-yunohost.md.
    # Repli sur le plus restrictif si une valeur inattendue arrivait ici
    # (défense en profondeur, la validation principale est déjà faite dans app.py).
    permission_group = visibility if visibility in ("admins", "all_users", "visitors") else "admins"
    args_string = (
        f"domain={target_domain}"
        f"&path={target_path}"
        f"&redirect_type=reverseproxy"
        f"&target=http://127.0.0.1:{host_port}"
        f"&init_main_permission={permission_group}"
    )

    apps_before = {a["id"] for a in json.loads(
        _run_sudo(["yunohost", "app", "list", "--output-as", "json"], t("err_list_apps", lang), lang)
    )["apps"]}

    try:
        _run_sudo(
            ["yunohost", "app", "install", "redirect", "--label", slug, "-a", args_string],
            t("err_expose_app", lang),
            lang,
        )
    except DockerConnectorError:
        # Ne laisse pas un conteneur (ni un volume) orphelin si l'exposition échoue.
        try:
            c = docker_client.containers.get(container_name)
            c.stop()
            c.remove()
        except docker.errors.NotFound:
            pass
        if volume_name:
            try:
                docker_client.volumes.get(volume_name).remove()
            except docker.errors.NotFound:
                pass
        raise

    apps_after = {a["id"] for a in json.loads(
        _run_sudo(["yunohost", "app", "list", "--output-as", "json"], t("err_list_apps", lang), lang)
    )["apps"]}
    new_app_ids = apps_after - apps_before
    yunohost_app_id = next(iter(new_app_ids), None)

    # --- Logo Docker Gate sur l'instance "redirect" exposée (best-effort :
    # une icône manquante ne doit jamais faire échouer une création qui a
    # par ailleurs réussi) ---
    if yunohost_app_id:
        try:
            _run_sudo(
                ["install", "-o", "root", "-g", "root", "-m", "0644",
                 str(CHILD_LOGO_SOURCE), f"/usr/share/yunohost/applogos/{yunohost_app_id}.png"],
                t("err_apply_child_logo_admin", lang),
                lang,
            )
        except DockerConnectorError as e:
            warnings.append(t("warn_child_logo_admin_failed", lang, error=e))

        try:
            _run_sudo(
                ["yunohost", "user", "permission", "update", f"{yunohost_app_id}.main",
                 "--logo", str(CHILD_LOGO_SOURCE)],
                t("err_apply_child_logo_portal", lang),
                lang,
            )
        except DockerConnectorError as e:
            warnings.append(t("warn_child_logo_portal_failed", lang, error=e))

    entry = {
        "slug": slug,
        "image": image,
        "container_name": container_name,
        "container_port": container_port,
        "host_port": host_port,
        "domain": target_domain,
        "path": target_path,
        "mode": mode,
        "visibility": permission_group,
        "yunohost_app_id": yunohost_app_id,
        "volume_name": volume_name,
        "data_path": data_path or None,
        "env_var_keys": sorted(env_vars.keys()) if env_vars else [],
    }
    apps = _load_state()
    apps.append(entry)
    _save_state(apps)
    entry["warnings"] = warnings
    return entry


def remove_docker_app(slug, lang, delete_data=False, delete_domain=False):
    """Supprime une app en 3 couches distinctes, vérifiées séparément
    (règle #30 — vérification multi-niveaux, leçon du 10/07/2026) :
    1) permission SSO + conf nginx (via `yunohost app remove`)
    2) conteneur Docker
    3) entrée dans notre fichier d'état

    delete_data (défaut False) : voir create_docker_app — jamais supprimé
    par défaut, case à cocher explicite requise.

    delete_domain (défaut False, pertinent seulement en mode "subdomain") :
    si coché, supprime aussi le domaine YunoHost dédié créé pour cette app.
    Point de vigilance propre à une architecture multi-VM avec TLS-passthrough
    (comme celle de BYRTN) : ceci ne nettoie PAS l'entrée de passthrough sur
    l'éventuelle VM relais (hors de portée de cette app) — à retirer à la main
    si besoin.

    Chaque étape est tentée indépendamment (best-effort) : l'échec d'une
    étape n'empêche jamais les suivantes de s'exécuter, et l'entrée est
    systématiquement retirée du fichier d'état à la fin — un échec partiel
    ne doit jamais laisser Docker Gate dans un état incohérent où il
    "croit" qu'une app existe encore alors qu'elle a été partiellement
    démantelée (durci le 15/07/2026, suite à un audit de robustesse : avant
    cette correction, un échec inattendu à une étape intermédiaire pouvait
    interrompre toute la suppression sans jamais mettre à jour l'état).
    Les échecs sont remontés comme avertissements (voir entry["warnings"]
    retourné) plutôt que de bloquer, cohérent avec le traitement déjà en
    place pour la création (voir create_docker_app).
    """
    apps = _load_state()
    entry = next((a for a in apps if a["slug"] == slug), None)
    if entry is None:
        raise DockerConnectorError(t("err_unknown_app", lang, slug=slug))

    warnings = []

    if entry.get("yunohost_app_id"):
        try:
            _run_sudo(
                ["yunohost", "app", "remove", entry["yunohost_app_id"]],
                t("err_remove_yunohost_exposure", lang, slug=slug),
                lang,
            )
        except DockerConnectorError as e:
            warnings.append(str(e))

    try:
        container = docker_client.containers.get(entry["container_name"])
        container.stop()
        container.remove()
    except docker.errors.NotFound:
        pass
    except docker.errors.APIError as e:
        warnings.append(t("err_remove_container", lang, name=entry["container_name"], error=e))

    if delete_data and entry.get("volume_name"):
        try:
            docker_client.volumes.get(entry["volume_name"]).remove()
        except docker.errors.NotFound:
            pass
        except docker.errors.APIError as e:
            warnings.append(t("err_remove_volume", lang, name=entry["volume_name"], error=e))

    if delete_domain and entry.get("mode") == "subdomain":
        try:
            _run_sudo(
                ["yunohost", "domain", "remove", entry["domain"]],
                t("err_remove_domain", lang, domain=entry["domain"]),
                lang,
            )
        except DockerConnectorError as e:
            warnings.append(str(e))

    # Toujours retirer l'entrée du fichier d'état, même en cas d'échec
    # partiel ci-dessus — un résidu réel (conteneur/volume/domaine non
    # supprimé) reste détectable et traitable depuis la page Audit &
    # nettoyage, plutôt que de bloquer indéfiniment la suppression.
    apps = [a for a in apps if a["slug"] != slug]
    _save_state(apps)

    return warnings


# =================================================
# AUDIT DES RÉSIDUS (étape 3, 12/07/2026)
# =================================================
# Principe : Docker Gate doit pouvoir retrouver tout seul ce qu'il a
# laissé traîner (échecs partiels, tests oubliés) plutôt que de compter sur
# l'utilisateur pour y penser à chaque fois. Chaque catégorie a un niveau de
# risque différent : les conteneurs orphelins et les images inutilisées sont
# sûrs à nettoyer (aucune perte de configuration/données réelle), les volumes
# orphelins peuvent contenir de vraies données (action prudente, un par un,
# jamais groupée), les domaines vides ne sont jamais supprimés automatiquement
# (juste signalés — un domaine peut avoir une utilité hors de la connaissance
# de cette app).

def find_orphan_containers():
    """Conteneurs Docker nommés 'docker-gate-*' mais absents de notre
    fichier d'état — reliquats d'une création/suppression interrompue."""
    known_names = {a["container_name"] for a in _load_state()}
    orphans = []
    for c in docker_client.containers.list(all=True):
        if c.name.startswith("docker-gate-") and c.name not in known_names:
            orphans.append({"name": c.name, "status": c.status, "image": c.image.tags})
    return orphans


def find_orphan_volumes():
    """Volumes Docker nommés 'docker-gate-*-data' mais absents de notre
    fichier d'état — jamais supprimés en masse, un par un et sur confirmation
    explicite (peuvent contenir de vraies données)."""
    known_volumes = {a["volume_name"] for a in _load_state() if a.get("volume_name")}
    orphans = []
    for v in docker_client.volumes.list():
        if v.name.startswith("docker-gate-") and v.name.endswith("-data") and v.name not in known_volumes:
            orphans.append({"name": v.name})
    return orphans


def find_dangling_images():
    """Images Docker 'dangling' (sans nom, sans conteneur les utilisant) —
    résidu standard et sûr de Docker, indépendant de nos propres apps."""
    images = docker_client.images.list(filters={"dangling": True})
    return [{"id": img.short_id, "size_mb": round(img.attrs.get("Size", 0) / (1024 * 1024), 1)} for img in images]


def remove_orphan_container(name, lang):
    """Supprime un conteneur orphelin précis (jamais en masse)."""
    known_names = {a["container_name"] for a in _load_state()}
    if name in known_names or not name.startswith("docker-gate-"):
        raise DockerConnectorError(t("err_container_not_orphan", lang))
    try:
        c = docker_client.containers.get(name)
        c.stop()
        c.remove()
    except docker.errors.NotFound:
        pass


def remove_orphan_volume(name, lang):
    """Supprime un volume orphelin précis (jamais en masse)."""
    known_volumes = {a["volume_name"] for a in _load_state() if a.get("volume_name")}
    if name in known_volumes or not (name.startswith("docker-gate-") and name.endswith("-data")):
        raise DockerConnectorError(t("err_volume_not_orphan", lang))
    try:
        docker_client.volumes.get(name).remove()
    except docker.errors.NotFound:
        pass


def prune_dangling_images():
    """Nettoie toutes les images dangling — opération standard et sûre de
    Docker (équivalent de `docker image prune -f`), aucune image utilisée par
    un conteneur existant n'est jamais concernée."""
    result = docker_client.images.prune(filters={"dangling": True})
    return result.get("SpaceReclaimed", 0)


def find_empty_domains(lang):
    """Domaines YunoHost sans aucune app installée dessus — signalés
    uniquement, JAMAIS supprimés automatiquement (un domaine peut avoir une
    utilité que cette app ne connaît pas)."""
    domains = existing_domains(lang)
    known_apps_domains = {a["domain"] for a in _load_state()}
    empty = []
    for d in domains:
        info_raw = _run_sudo(
            ["yunohost", "domain", "info", d, "--output-as", "json"],
            t("err_verify_domain", lang, domain=d),
            lang,
        )
        info = json.loads(info_raw)
        apps_on_domain = info.get("apps", [])
        if not apps_on_domain and d not in known_apps_domains:
            empty.append(d)
    return empty
