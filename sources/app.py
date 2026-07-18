#!/usr/bin/env python3
"""
Docker Gate — interface d'administration YunoHost
Étape 2 (11/07/2026) : formulaire "+ Ajouter une app Docker" fonctionnel,
modes chemin et sous-domaine dédié, suppression avec vérification à 3
niveaux (règle #30).

Internationalisation (15/07/2026) : anglais par défaut, français
sélectionnable dans l'interface (cookie longue durée) et dès l'installation
(voir manifest.toml, question default_language + data/default_language.txt
écrit par les scripts install/upgrade/restore).
"""
import hmac
import secrets
import threading
from pathlib import Path

from flask import Flask, abort, render_template, request, redirect, session, url_for, flash, jsonify, make_response

import ynh_manager
import progress
import i18n

# Endpoints qui modifient un état réel (création/suppression d'app, de
# conteneur orphelin, de volume orphelin, nettoyage d'images) — protégés par
# jeton CSRF. /parse_input n'en a pas besoin : purement en lecture (aucun
# effet de bord), et sa réponse JSON n'est de toute façon pas lisible depuis
# une origine tierce (pas d'en-tête CORS renvoyé par Flask par défaut).
CSRF_PROTECTED_ENDPOINTS = {
    "add",
    "remove",
    "audit_remove_container",
    "audit_remove_volume",
    "audit_prune_images",
}

LANG_COOKIE_NAME = "docker_gate_lang"
LANG_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 an

# Version affichée dans le footer (base.html) — tenue à jour manuellement en
# même temps que `version` dans manifest.toml (partie avant `~ynh`), pas
# lue dynamiquement pour éviter une dépendance de parsing au manifeste au
# runtime pour un simple affichage.
APP_VERSION = "1.2"

app = Flask(__name__)


def _load_or_create_secret_key():
    """Génère une clé secrète aléatoire au premier démarrage et la conserve
    dans data/ (même dossier que apps.json, déjà protégé par les permissions
    posées à l'installation — chown/chmod sur install_dir). Remplace une
    ancienne clé codée en dur dans le code source (mauvaise pratique pour un
    dépôt destiné à devenir public, même si le risque réel était faible tant
    qu'aucune donnée de session sensible n'est stockée)."""
    key_file = Path(__file__).parent / "data" / ".secret_key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_hex(32)
    key_file.write_text(key)
    key_file.chmod(0o600)
    return key


app.secret_key = _load_or_create_secret_key()


def _default_lang_from_install():
    """Langue choisie à l'installation (voir manifest.toml, question
    default_language) — sert de repli uniquement tant que l'utilisateur n'a
    jamais choisi explicitement dans l'interface (pas de cookie posé)."""
    default_lang_file = Path(__file__).parent / "data" / "default_language.txt"
    if default_lang_file.exists():
        return i18n.normalize_lang(default_lang_file.read_text().strip())
    return i18n.DEFAULT_LANG


def get_lang():
    """Langue courante : cookie posé par l'utilisateur (voir /set_language)
    en priorité, sinon la langue choisie à l'installation, sinon l'anglais
    par défaut. Jamais déduite du contexte Flask à l'intérieur de
    ynh_manager.py — capturée ici et passée explicitement (voir docstring
    de create_docker_app)."""
    cookie_lang = request.cookies.get(LANG_COOKIE_NAME)
    if cookie_lang:
        return i18n.normalize_lang(cookie_lang)
    return _default_lang_from_install()


class PrefixMiddleware:
    """Rend Flask conscient du préfixe de chemin sous lequel nginx le monte
    (ex: /docker-gate), transmis via l'en-tête X-Forwarded-Prefix défini
    dans conf/nginx.conf. Sans ça, toute redirection générée par Flask
    casserait en sortant du sous-chemin (point de vigilance noté depuis
    l'étape 1)."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        prefix = environ.get("HTTP_X_FORWARDED_PREFIX", "")
        if prefix and prefix != "/":
            environ["SCRIPT_NAME"] = prefix
            path_info = environ.get("PATH_INFO", "")
            if path_info.startswith(prefix):
                environ["PATH_INFO"] = path_info[len(prefix):]
        return self.wsgi_app(environ, start_response)


app.wsgi_app = PrefixMiddleware(app.wsgi_app)


def _get_csrf_token():
    """Jeton CSRF stocké dans la session signée Flask (voir secret_key
    ci-dessus) — un par session navigateur, généré au premier accès."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = _get_csrf_token
app.jinja_env.globals["t"] = lambda key, **kwargs: i18n.t(key, get_lang(), **kwargs)
app.jinja_env.globals["current_lang"] = get_lang
app.jinja_env.globals["app_version"] = APP_VERSION


@app.before_request
def _check_csrf():
    if request.method != "POST" or request.endpoint not in CSRF_PROTECTED_ENDPOINTS:
        return
    expected = session.get("csrf_token")
    submitted = request.form.get("csrf_token", "")
    if not expected or not hmac.compare_digest(expected, submitted):
        abort(400, i18n.t("flash_csrf_invalid", get_lang()))


@app.route("/set_language/<lang>")
def set_language(lang):
    """Changement de langue depuis l'interface (voir sélecteur dans
    base.html) — posé en cookie longue durée, pas juste en session, pour que
    le choix survive à une fermeture de navigateur."""
    lang = i18n.normalize_lang(lang)
    target = request.referrer or url_for("index")
    resp = make_response(redirect(target))
    resp.set_cookie(LANG_COOKIE_NAME, lang, max_age=LANG_COOKIE_MAX_AGE)
    return resp


@app.route("/")
def index():
    apps = ynh_manager.list_apps(get_lang())
    return render_template("index.html", apps=apps)


@app.route("/add", methods=["GET", "POST"])
def add():
    lang = get_lang()
    if request.method == "GET":
        domains = ynh_manager.existing_domains(lang)
        return render_template("add.html", domains=domains)

    slug = request.form.get("slug", "").strip().lower()
    image = request.form.get("image", "").strip()
    container_port = request.form.get("container_port", "").strip()
    mode = request.form.get("mode", "path")
    domain = request.form.get("domain", "").strip()
    domain_parent = request.form.get("domain_parent", "").strip()
    path = request.form.get("path", "").strip()
    new_subdomain = request.form.get("new_subdomain", "").strip().lower()
    # Modèle de permission natif YunoHost à 3 groupes (audit 17/07/2026,
    # docs/02-wappos/audits/2026-07-17-audit-permissions-yunohost.md) —
    # valeur repliée sur "admins" (le plus restrictif) si absente/invalide.
    visibility = request.form.get("visibility", "admins").strip()
    if visibility not in ("admins", "all_users", "visitors"):
        visibility = "admins"
    data_path = request.form.get("data_path", "").strip()
    env_vars_text = request.form.get("env_vars", "").strip()
    url_env_var = request.form.get("url_env_var", "").strip()
    reuse_existing_domain = request.form.get("reuse_existing_domain") == "on"

    try:
        env_vars = ynh_manager.parse_env_vars_text(env_vars_text, lang) if env_vars_text else {}
    except ynh_manager.DockerConnectorError as e:
        domains = ynh_manager.existing_domains(lang)
        return render_template("add.html", domains=domains, error=str(e), form=request.form)

    steps = ynh_manager.build_create_steps(mode, has_data=bool(data_path))
    job_id = progress.create_job(steps)

    def run_creation():
        try:
            entry = ynh_manager.create_docker_app(
                slug=slug,
                image=image,
                container_port=container_port,
                mode=mode,
                domain=domain,
                domain_parent=domain_parent,
                path=path,
                new_subdomain=new_subdomain,
                visibility=visibility,
                lang=lang,
                data_path=data_path,
                env_vars=env_vars,
                url_env_var=url_env_var,
                reuse_existing_domain=reuse_existing_domain,
                on_step=lambda label: progress.advance(job_id, label),
            )
            progress.finish(job_id, warnings=entry.get("warnings", []))
        except ynh_manager.DockerConnectorError as e:
            progress.fail(job_id, str(e))
        except Exception as e:
            # Filet de sécurité : toute erreur inattendue doit quand même
            # arrêter proprement le suivi de progression, pas le laisser
            # tourner indéfiniment (règle #1 — jamais d'échec silencieux).
            progress.fail(job_id, i18n.t("flash_unexpected_error", lang, error=e))

    threading.Thread(target=run_creation, daemon=True).start()
    return redirect(url_for("show_progress", job_id=job_id, slug=slug))


@app.route("/check_subdomain")
def check_subdomain():
    new_subdomain = request.args.get("new_subdomain", "").strip().lower()
    domain_parent = request.args.get("domain_parent", "").strip()
    if not new_subdomain or not domain_parent:
        return jsonify({"status": "invalid"})
    result = ynh_manager.check_subdomain_status(new_subdomain, domain_parent, get_lang())
    return jsonify(result)


@app.route("/check_path")
def check_path():
    domain = request.args.get("domain", "").strip()
    path = request.args.get("path", "").strip()
    if not domain or not path:
        return jsonify({"status": "invalid"})
    result = ynh_manager.check_path_status(domain, path, get_lang())
    return jsonify(result)


@app.route("/parse_input", methods=["POST"])
def parse_input():
    lang = get_lang()
    payload = request.get_json(silent=True) or {}
    url = payload.get("url", "").strip()

    if url:
        try:
            raw_text = ynh_manager.fetch_compose_from_url(url, lang)
        except ynh_manager.DockerConnectorError as e:
            return jsonify({"ok": False, "error": str(e)})
    else:
        raw_text = payload.get("text", "")

    try:
        result = ynh_manager.smart_parse_input(raw_text, lang)
        if url:
            result["raw_text"] = raw_text
        return jsonify({"ok": True, **result})
    except ynh_manager.DockerConnectorError as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/progress/<job_id>")
def show_progress(job_id):
    job = progress.get_job(job_id)
    if job is None:
        flash(i18n.t("flash_progress_not_found", get_lang()), "error")
        return redirect(url_for("index"))
    slug = request.args.get("slug", "")
    return render_template("progress.html", job_id=job_id, steps=job["steps"], slug=slug)


@app.route("/progress/<job_id>/status")
def progress_status(job_id):
    job = progress.get_job(job_id)
    if job is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(job)


@app.route("/remove/<slug>", methods=["POST"])
def remove(slug):
    lang = get_lang()
    delete_data = request.form.get("delete_data") == "on"
    delete_domain = request.form.get("delete_domain") == "on"
    try:
        warnings = ynh_manager.remove_docker_app(slug, lang, delete_data=delete_data, delete_domain=delete_domain)
        parts = [i18n.t("flash_app_removed", lang, slug=slug)]
        parts.append(i18n.t("flash_data_removed", lang) if delete_data else i18n.t("flash_data_kept", lang))
        if delete_domain:
            parts.append(i18n.t("flash_domain_removed", lang))
        flash(" ".join(parts), "success")
        for w in warnings:
            flash(w, "warning")
    except ynh_manager.DockerConnectorError as e:
        flash(str(e), "error")
    except Exception as e:
        # Audit chantier 5 (17/07/2026, cas limites) : sans ce filet, une
        # erreur inattendue ici (pas une DockerConnectorError) laissait
        # Flask afficher une page 500 brute au lieu d'un message clair —
        # même principe que le filet déjà en place pour la création d'app.
        flash(i18n.t("flash_unexpected_error", lang, error=e), "error")
    return redirect(url_for("index"))


@app.route("/audit")
def audit():
    lang = get_lang()
    # Audit chantier 5 (17/07/2026, cas limites) : avant ce correctif, un
    # incident transitoire sur UN SEUL de ces 4 contrôles (ex: `yunohost
    # domain list` via sudo -n indisponible un court instant) faisait
    # planter TOUTE la page avec une erreur 500 brute, y compris les 3
    # autres contrôles qui, eux, avaient réussi. Chacun est maintenant
    # isolé : un échec dégrade proprement (liste vide + avertissement),
    # sans jamais empêcher d'afficher le reste de la page.
    def _safe(fn, *args):
        try:
            return fn(*args)
        except Exception as e:
            flash(i18n.t("flash_unexpected_error", lang, error=e), "warning")
            return []

    orphan_containers = _safe(ynh_manager.find_orphan_containers)
    orphan_volumes = _safe(ynh_manager.find_orphan_volumes)
    dangling_images = _safe(ynh_manager.find_dangling_images)
    empty_domains = _safe(ynh_manager.find_empty_domains, lang)
    return render_template(
        "audit.html",
        orphan_containers=orphan_containers,
        orphan_volumes=orphan_volumes,
        dangling_images=dangling_images,
        empty_domains=empty_domains,
    )


@app.route("/audit/remove_container/<name>", methods=["POST"])
def audit_remove_container(name):
    lang = get_lang()
    try:
        ynh_manager.remove_orphan_container(name, lang)
        flash(i18n.t("flash_orphan_container_removed", lang, name=name), "success")
    except ynh_manager.DockerConnectorError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(i18n.t("flash_unexpected_error", lang, error=e), "error")
    return redirect(url_for("audit"))


@app.route("/audit/remove_volume/<name>", methods=["POST"])
def audit_remove_volume(name):
    lang = get_lang()
    try:
        ynh_manager.remove_orphan_volume(name, lang)
        flash(i18n.t("flash_orphan_volume_removed", lang, name=name), "success")
    except ynh_manager.DockerConnectorError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(i18n.t("flash_unexpected_error", lang, error=e), "error")
    return redirect(url_for("audit"))


@app.route("/audit/prune_images", methods=["POST"])
def audit_prune_images():
    lang = get_lang()
    try:
        freed = ynh_manager.prune_dangling_images()
        freed_mb = round(freed / (1024 * 1024), 1)
        flash(i18n.t("flash_images_pruned", lang, mb=freed_mb), "success")
    except Exception as e:
        flash(i18n.t("flash_prune_error", lang, error=e), "error")
    return redirect(url_for("audit"))


@app.route("/healthz")
def healthz():
    return {"status": "ok", "step": 2}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9200)
