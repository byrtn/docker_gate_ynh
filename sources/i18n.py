"""
Docker Gate — internationalisation FR/EN.

Mécanisme volontairement léger (dictionnaire Python, pas de compilation
.po/.mo) plutôt que Flask-Babel — cohérent avec le style minimaliste du
reste du projet, et suffisant pour le volume de texte de cette app.

Anglais par défaut (cohérent avec la publication publique à venir),
français sélectionnable dans l'interface (voir /set_language dans app.py)
et dès l'installation (voir manifest.toml, question default_language).

Chaque clé porte le texte des deux langues. Les messages paramétrés
utilisent la syntaxe `.format(**kwargs)` (ex: "{domain}").
"""

DEFAULT_LANG = "en"
LANGS = ("en", "fr")

STRINGS = {
    # --- Étapes de progression (clés stables, jamais affichées telles
    # quelles — voir build_create_steps dans ynh_manager.py et progress.html) ---
    "step_check_params": {"en": "Checking parameters", "fr": "Vérification des paramètres"},
    "step_pick_port": {"en": "Selecting a free port", "fr": "Sélection d'un port libre"},
    "step_create_domain": {"en": "Creating the YunoHost domain", "fr": "Création du domaine YunoHost"},
    "step_dns_diag": {"en": "DNS diagnosis", "fr": "Diagnostic DNS"},
    "step_web_diag": {"en": "Web diagnosis", "fr": "Diagnostic Web"},
    "step_get_cert": {"en": "Obtaining the Let's Encrypt certificate", "fr": "Obtention du certificat Let's Encrypt"},
    "step_check_cert": {"en": "Checking the obtained certificate", "fr": "Vérification du certificat obtenu"},
    "step_create_volume": {"en": "Creating the data volume", "fr": "Création du volume de données"},
    "step_run_container": {"en": "Starting the Docker container", "fr": "Lancement du conteneur Docker"},
    "step_expose_app": {"en": "Exposing via YunoHost (nginx + SSO)", "fr": "Exposition via YunoHost (nginx + SSO)"},

    # --- Erreurs / avertissements (ynh_manager.py) ---
    "err_no_free_port": {
        "en": "No free port in the 9100-9999 range.",
        "fr": "Aucun port libre dans la plage 9100-9999.",
    },
    "err_sudo_detail": {
        "en": "{message}\n\nTechnical detail:\n{detail}",
        "fr": "{message}\n\nDétail technique :\n{detail}",
    },
    "err_list_domains": {
        "en": "Unable to retrieve the list of YunoHost domains.",
        "fr": "Impossible de récupérer la liste des domaines YunoHost.",
    },
    "err_https_only": {
        "en": "Only https:// URLs are accepted.",
        "fr": "Seules les URLs en https:// sont acceptées.",
    },
    "err_fetch_url": {
        "en": "Unable to fetch this file: {error}",
        "fr": "Impossible de récupérer ce fichier : {error}",
    },
    "err_file_too_large": {
        "en": "This file is too large to be a valid docker-compose.yml.",
        "fr": "Ce fichier est trop volumineux pour être un docker-compose.yml valide.",
    },
    "err_pull_image": {
        "en": "Unable to download image '{image}': {error}",
        "fr": "Impossible de télécharger l'image '{image}' : {error}",
    },
    "err_not_docker_run": {
        "en": "This text doesn't look like a valid 'docker run ...' command.",
        "fr": "Ce texte ne ressemble pas à une commande 'docker run ...' valide.",
    },
    "err_parse_command": {
        "en": "Unable to analyze this command: {error}",
        "fr": "Impossible d'analyser cette commande : {error}",
    },
    "err_no_docker_run": {
        "en": "This command doesn't contain 'docker run'.",
        "fr": "Cette commande ne contient pas 'docker run'.",
    },
    "err_no_image_in_command": {
        "en": "Unable to find the image name in this command.",
        "fr": "Impossible de trouver le nom de l'image dans cette commande.",
    },
    "err_nothing_to_analyze": {
        "en": "Nothing to analyze — paste an image, a docker run command, or a docker-compose.yml.",
        "fr": "Rien à analyser — colle une image, une commande docker run, ou un docker-compose.yml.",
    },
    "err_unrecognized_format": {
        "en": "Unrecognized format — paste either an image name, a 'docker run ...' command, or a docker-compose.yml.",
        "fr": "Format non reconnu — colle soit un nom d'image, soit une commande 'docker run ...', soit un docker-compose.yml.",
    },
    "err_invalid_compose": {
        "en": "This text doesn't look like a valid docker-compose.yml: {error}",
        "fr": "Ce texte ne ressemble pas à un docker-compose.yml valide : {error}",
    },
    "err_invalid_compose_notdict": {
        "en": "This text doesn't look like a valid docker-compose.yml.",
        "fr": "Ce texte ne ressemble pas à un docker-compose.yml valide.",
    },
    "err_no_service_found": {
        "en": "No service found in this docker-compose.yml.",
        "fr": "Aucun service trouvé dans ce docker-compose.yml.",
    },
    "err_unrecognized_service_format": {
        "en": "Unrecognized service format in this docker-compose.yml.",
        "fr": "Format de service non reconnu dans ce docker-compose.yml.",
    },
    "err_nothing_extracted": {
        "en": "No usable information found (no image, port, volume, or environment variable) in this docker-compose.yml.",
        "fr": "Aucune information exploitable trouvée (ni image, ni port, ni volume, ni variable d'environnement) dans ce docker-compose.yml.",
    },
    "err_invalid_env_line": {
        "en": "Invalid line {line_no} in the environment variables: '{line}' (expected format: KEY=value).",
        "fr": "Ligne {line_no} invalide dans les variables d'environnement : '{line}' (format attendu : CLE=valeur).",
    },
    "err_verify_domain": {
        "en": "Unable to verify domain {domain}.",
        "fr": "Impossible de vérifier le domaine {domain}.",
    },
    "err_list_apps": {
        "en": "Unable to list YunoHost apps.",
        "fr": "Impossible de lister les apps YunoHost.",
    },
    "err_invalid_slug": {
        "en": "The app name must contain only lowercase letters, digits, and hyphens (2 to 31 characters).",
        "fr": "Le nom de l'app doit contenir uniquement des lettres minuscules, chiffres et tirets (2 à 31 caractères).",
    },
    "err_slug_already_used": {
        "en": "An app named '{slug}' already exists.",
        "fr": "Une app nommée '{slug}' existe déjà.",
    },
    "err_port_not_a_number": {
        "en": "The container's internal port must be a number.",
        "fr": "Le port interne du conteneur doit être un nombre.",
    },
    "err_invalid_subdomain": {
        "en": "Invalid subdomain name.",
        "fr": "Nom de sous-domaine invalide.",
    },
    "err_create_subdomain": {
        "en": "Unable to create the subdomain {domain}. Check that the DNS record exists (or that the automatic registrar is configured) before retrying.",
        "fr": "Impossible de créer le sous-domaine {domain}. Vérifie que l'enregistrement DNS existe (ou que le registrar automatique est configuré) avant de réessayer.",
    },
    "warn_dns_diag_failed": {
        "en": "DNS diagnosis failed for {domain} — check that your registrar's DNS zone points to this server.",
        "fr": "Diagnostic DNS en échec pour {domain} — pense à vérifier que la zone DNS de ton registrar pointe bien vers ce serveur.",
    },
    "warn_web_diag_failed": {
        "en": "Web diagnosis failed for {domain} — the app might not be reachable until this is resolved.",
        "fr": "Diagnostic Web en échec pour {domain} — l'app pourrait ne pas être joignable tant que ce point n'est pas résolu.",
    },
    "warn_cert_not_obtained": {
        "en": (
            "Let's Encrypt certificate not obtained for {domain} — the app is already created and working. "
            "If your DNS zone isn't configured with your registrar yet, now is the time to do it. If this server "
            "is behind a relay/reverse-proxy TLS-passthrough (another server that receives public traffic and "
            "forwards it here), also remember to declare this domain on that relay (YunoHost tls_passthrough_list "
            "setting, or equivalent depending on your relay) — otherwise Let's Encrypt validation cannot reach it. "
            "Then request the certificate again from the YunoHost admin panel (Domains > {domain} > Certificate) — "
            "YunoHost NEVER does this automatically for a domain left self-signed, only to renew an already-valid "
            "certificate. If DNS and any relay were already fine, a simple retry is usually enough."
        ),
        "fr": (
            "Certificat Let's Encrypt non obtenu pour {domain} — l'app est déjà créée et fonctionnelle. Si ta zone "
            "DNS n'est pas encore paramétrée chez ton registrar, c'est le moment de le faire. Si ce serveur est "
            "derrière un relais/reverse-proxy TLS-passthrough (un autre serveur qui reçoit le trafic public et le "
            "redirige vers celui-ci), pense aussi à déclarer ce domaine sur ce relais (réglage YunoHost "
            "tls_passthrough_list, ou équivalent selon ton relais) — sinon la validation Let's Encrypt ne peut pas "
            "l'atteindre. Puis redemande le certificat depuis l'admin YunoHost (Domaines > {domain} > Certificat) — "
            "YunoHost ne le fait JAMAIS tout seul pour un domaine resté en auto-signé, seulement pour renouveler un "
            "certificat déjà valide. Si le DNS et le relais éventuel étaient déjà bons, un simple nouvel essai "
            "suffit généralement."
        ),
    },
    "err_verify_cert_status": {
        "en": "Unable to verify the certificate status for {domain}.",
        "fr": "Impossible de vérifier le statut du certificat pour {domain}.",
    },
    "warn_verify_cert_failed": {
        "en": "Unable to verify the certificate for {domain}: {error}",
        "fr": "Impossible de vérifier le certificat de {domain} : {error}",
    },
    "warn_cert_not_letsencrypt": {
        "en": (
            "{domain} currently only has a {ca_type} certificate (not yet Let's Encrypt) — the app already works, "
            "but visitors will see a security warning in their browser in the meantime. If your DNS zone isn't "
            "configured with your registrar yet, do it now. If this server is behind a relay/reverse-proxy "
            "TLS-passthrough, also check that this domain is properly declared there — otherwise Let's Encrypt "
            "validation cannot reach this server. If everything was already fine, a simple retry is usually enough "
            "(YunoHost sometimes blocks the very first attempt on a freshly created domain). Request the "
            "certificate again from the YunoHost admin panel (Domains > {domain} > Certificate)."
        ),
        "fr": (
            "{domain} n'a pour l'instant qu'un certificat {ca_type} (pas encore Let's Encrypt) — l'app fonctionne "
            "déjà, mais les visiteurs verront un avertissement de sécurité dans leur navigateur en attendant. Si ta "
            "zone DNS n'est pas encore paramétrée chez ton registrar, fais-le maintenant. Si ce serveur est derrière "
            "un relais/reverse-proxy TLS-passthrough, vérifie aussi que ce domaine y est bien déclaré — sans ça, la "
            "validation Let's Encrypt ne peut pas atteindre ce serveur. Si tout était déjà bon, un simple nouvel "
            "essai suffit généralement (YunoHost bloque parfois le tout premier essai sur un domaine tout juste "
            "créé). Redemande le certificat depuis l'admin YunoHost (Domaines > {domain} > Certificat)."
        ),
    },
    "err_create_volume": {
        "en": "Unable to create the data volume: {error}",
        "fr": "Impossible de créer le volume de données : {error}",
    },
    "err_run_container": {
        "en": "Docker was unable to start the container: {error}",
        "fr": "Docker n'a pas pu lancer le conteneur : {error}",
    },
    "err_expose_app": {
        "en": "Exposing via the YunoHost 'redirect' app failed. The Docker container was started but isn't exposed yet.",
        "fr": "L'exposition via l'app YunoHost 'redirect' a échoué. Le conteneur Docker a été lancé mais n'est pas encore exposé.",
    },
    "err_unknown_app": {
        "en": "No app named '{slug}' is known.",
        "fr": "Aucune app nommée '{slug}' n'est connue.",
    },
    "err_remove_yunohost_exposure": {
        "en": "Unable to remove the YunoHost exposure for '{slug}'.",
        "fr": "Impossible de supprimer l'exposition YunoHost de '{slug}'.",
    },
    "err_remove_container": {
        "en": "Unable to remove the Docker container '{name}': {error}",
        "fr": "Impossible de supprimer le conteneur Docker '{name}' : {error}",
    },
    "err_remove_volume": {
        "en": "Unable to remove the volume '{name}': {error}",
        "fr": "Impossible de supprimer le volume '{name}' : {error}",
    },
    "err_remove_domain": {
        "en": (
            "Unable to remove the YunoHost domain {domain}. The app and container were removed successfully, "
            "but the domain is still registered."
        ),
        "fr": (
            "Impossible de supprimer le domaine YunoHost {domain}. L'app et le conteneur ont bien été supprimés, "
            "mais le domaine reste déclaré."
        ),
    },
    "err_container_not_orphan": {
        "en": "This container isn't recognized as an orphan, removal refused for safety.",
        "fr": "Ce conteneur n'est pas reconnu comme orphelin, suppression refusée par sécurité.",
    },
    "err_volume_not_orphan": {
        "en": "This volume isn't recognized as an orphan, removal refused for safety.",
        "fr": "Ce volume n'est pas reconnu comme orphelin, suppression refusée par sécurité.",
    },

    # --- app.py (flash messages) ---
    "flash_app_removed": {"en": "App '{slug}' removed.", "fr": "App '{slug}' supprimée."},
    "flash_data_removed": {"en": "Data also removed.", "fr": "Données également supprimées."},
    "flash_data_kept": {"en": "Data kept.", "fr": "Données conservées."},
    "flash_domain_removed": {"en": "YunoHost domain also removed.", "fr": "Domaine YunoHost également supprimé."},
    "flash_orphan_container_removed": {"en": "Orphan container '{name}' removed.", "fr": "Conteneur orphelin '{name}' supprimé."},
    "flash_orphan_volume_removed": {"en": "Orphan volume '{name}' removed.", "fr": "Volume orphelin '{name}' supprimé."},
    "flash_images_pruned": {"en": "Unused images cleaned up ({mb} MB freed).", "fr": "Images inutilisées nettoyées ({mb} Mo libérés)."},
    "flash_prune_error": {"en": "Error while cleaning up images: {error}", "fr": "Erreur lors du nettoyage des images : {error}"},
    "flash_progress_not_found": {
        "en": "Progress tracking not found (the service may have restarted in the meantime).",
        "fr": "Suivi de progression introuvable (le service a peut-être redémarré entre-temps).",
    },
    "flash_csrf_invalid": {
        "en": "Request refused (invalid or expired security token) — reload the page and try again.",
        "fr": "Requête refusée (jeton de sécurité invalide ou expiré) — recharge la page et réessaie.",
    },
    "flash_unexpected_error": {"en": "Unexpected error: {error}", "fr": "Erreur inattendue : {error}"},

    # --- Templates : commun ---
    "btn_confirm": {"en": "Confirm?", "fr": "Confirmer ?"},
    # Note : le footer "Un produit BYRTN — souveraineté numérique." reste
    # volontairement TOUJOURS en français, dans les deux langues (demande
    # explicite de Patrick, 15/07/2026) — codé en dur dans base.html, pas
    # une clé de traduction ici.
    "btn_choose_file": {"en": "Choose file", "fr": "Choisir un fichier"},
    "no_file_chosen": {"en": "No file chosen", "fr": "Aucun fichier choisi"},

    # --- index.html ---
    "title_index": {"en": "Docker Gate — Home", "fr": "Docker Gate — Accueil"},
    "apps_installed_count": {
        "en": "{count} Docker app{plural} installed",
        "fr": "{count} app{plural} Docker installée{plural}",
    },
    "no_app_installed": {"en": "No Docker app installed yet.", "fr": "Aucune app Docker installée pour l'instant."},
    "click_to_add": {"en": "Click the button below to add one.", "fr": "Clique sur le bouton ci-dessous pour en ajouter une."},
    "open_link": {"en": "Open ↗", "fr": "Ouvrir ↗"},
    "public_label": {"en": "public", "fr": "public"},
    "private_label": {"en": "private", "fr": "privé"},
    "persistent_data_suffix": {"en": " — persistent data", "fr": " — données persistantes"},
    "checkbox_delete_data": {"en": "Also delete the data", "fr": "Supprimer aussi les données"},
    "checkbox_delete_domain": {"en": "Also delete the domain {domain}", "fr": "Supprimer aussi le domaine {domain}"},
    "btn_delete": {"en": "Delete", "fr": "Supprimer"},
    "btn_add_app": {"en": "+ Add a Docker app", "fr": "+ Ajouter une app Docker"},
    "btn_audit": {"en": "Audit & cleanup", "fr": "Audit & nettoyage"},
    "confirm_delete_with_extras": {
        "en": "Delete {slug}? The checked boxes (data and/or domain) will ALSO be permanently deleted.",
        "fr": "Supprimer {slug} ? Les cases cochées (données et/ou domaine) seront AUSSI supprimées définitivement.",
    },
    "confirm_delete_simple": {
        "en": "Permanently delete {slug}? (app + Docker container)",
        "fr": "Supprimer définitivement {slug} ? (app + conteneur Docker)",
    },

    # --- add.html ---
    "title_add": {"en": "Docker Gate — Add an app", "fr": "Docker Gate — Ajouter une app"},
    "h1_add": {"en": "Add a Docker app", "fr": "Ajouter une app Docker"},
    "raw_input_label": {
        "en": "Paste a Docker image, a docker run command, or a docker-compose.yml",
        "fr": "Colle une image Docker, une commande docker run, ou un docker-compose.yml",
    },
    "raw_input_placeholder": {
        "en": "vaultwarden/server:latest\n\nor\n\ndocker run -d --name vaultwarden -v /vw-data/:/data/ -p 80:80 vaultwarden/server:latest\n\nor a complete docker-compose.yml",
        "fr": "vaultwarden/server:latest\n\nou\n\ndocker run -d --name vaultwarden -v /vw-data/:/data/ -p 80:80 vaultwarden/server:latest\n\nou un docker-compose.yml complet",
    },
    "import_file_or_url": {"en": "Import a file or URL instead", "fr": "Importer un fichier ou une URL à la place"},
    "compose_url_placeholder": {
        "en": "URL (e.g. raw GitHub link to a docker-compose.yml)",
        "fr": "URL (ex: lien GitHub brut vers un docker-compose.yml)",
    },
    "btn_analyze": {"en": "Analyze", "fr": "Analyser"},
    "app_name_label": {"en": "App name", "fr": "Nom de l'app"},
    "app_name_placeholder": {"en": "e.g. uptime-kuma", "fr": "ex: uptime-kuma"},
    "app_name_help": {
        "en": "Lowercase letters, digits, and hyphens only. Used as the internal name — the address below can be different.",
        "fr": "Lettres minuscules, chiffres et tirets uniquement. Sert de nom interne — l'adresse ci-dessous peut être différente.",
    },
    "where_install_label": {"en": "Where do you want to install the app?", "fr": "Où souhaitez-vous installer l'application ?"},
    "mode_path_label": {"en": "In a directory", "fr": "Dans un répertoire"},
    "mode_subdomain_label": {"en": "On a dedicated subdomain", "fr": "Sur un sous-domaine dédié"},
    "mode_help": {
        "en": "Choose \"dedicated subdomain\" if the app doesn't work under a subpath (SPA-type interfaces, like Portainer).",
        "fr": "Choisis \"sous-domaine dédié\" si l'app ne fonctionne pas sous un sous-chemin (cas des interfaces type SPA, comme Portainer).",
    },
    "address_label": {"en": "Address", "fr": "Adresse"},
    "address_help": {
        "en": "Freely editable — doesn't need to match the app name.",
        "fr": "Modifiable librement — pas besoin d'être identique au nom de l'app.",
    },
    "dns_reminder": {
        "en": "📌 Don't forget: a DNS record for this subdomain must already exist with your registrar (or the automatic registrar must be configured in YunoHost).",
        "fr": "📌 N'oublie pas : un enregistrement DNS pour ce sous-domaine doit déjà exister chez ton registrar (ou le registrar automatique doit être configuré dans YunoHost).",
    },
    "checkbox_public": {"en": "Make this app public (otherwise, restricted to admins)", "fr": "Rendre cette app publique (sinon, accès restreint aux admins)"},
    "advanced_config": {
        "en": "Advanced configuration (pre-filled automatically, editable if needed)",
        "fr": "Configuration avancée (préremplie automatiquement, modifiable si besoin)",
    },
    "image_label": {"en": "Docker image", "fr": "Image Docker"},
    "port_label": {"en": "Container internal port", "fr": "Port interne du conteneur"},
    "data_path_label": {"en": "Persistent data (optional)", "fr": "Données persistantes (optionnel)"},
    "data_path_help": {
        "en": "A dedicated storage space will be created automatically and never removed without explicit confirmation.",
        "fr": "Un espace de stockage dédié sera créé automatiquement et ne sera jamais supprimé sans confirmation explicite.",
    },
    "url_env_var_label": {"en": "Base URL variable name (optional)", "fr": "Nom de la variable d'URL de base (optionnel)"},
    "url_env_var_help": {
        "en": "Auto-detected if present in what was analyzed. Its value is computed automatically from the address chosen above.",
        "fr": "Détectée automatiquement si présente dans ce qui a été analysé. Sa valeur est calculée toute seule à partir de l'adresse choisie plus haut.",
    },
    "other_env_vars_label": {"en": "Other environment variables (optional)", "fr": "Autres variables d'environnement (optionnel)"},
    "other_env_vars_help": {"en": "One variable per line, format KEY=value.", "fr": "Une variable par ligne, format CLE=valeur."},
    "btn_install": {"en": "Install", "fr": "Installer"},
    "js_paste_something": {"en": "Paste something to analyze first.", "fr": "Colle d'abord quelque chose à analyser."},
    "js_analyzing": {"en": "Analyzing...", "fr": "Analyse en cours..."},
    "js_review_prefilled": {
        "en": "Please review all pre-filled information below and correct/adapt if needed.",
        "fr": "Veuillez vérifier toutes les informations pré-remplies ci-dessous et corriger/adapter si nécessaire.",
    },
    "js_nothing_extracted": {"en": "Nothing found to extract — check the advanced mode.", "fr": "Rien trouvé à extraire — vérifie en mode avancé."},
    "js_comm_error": {"en": "Communication error with the server.", "fr": "Erreur de communication avec le serveur."},
    "js_path_available": {"en": "✓ {address} is available.", "fr": "✓ {address} est disponible."},
    "js_path_used": {
        "en": "✗ {address} already hosts another app{app_name} — choose another path.",
        "fr": "✗ {address} héberge déjà une autre app{app_name} — choisis un autre chemin.",
    },
    "js_subdomain_available": {"en": "✓ {domain} is available.", "fr": "✓ {domain} est disponible."},
    "js_subdomain_exists_empty": {
        "en": "⚠️ {domain} already exists but is empty (no app on it — probably left over from a previous attempt).",
        "fr": "⚠️ {domain} existe déjà mais est vide (aucune app dessus — probablement laissé par un essai précédent).",
    },
    "js_reuse_subdomain": {
        "en": "Reuse this subdomain as-is (recommended — avoids removing it manually)",
        "fr": "Réutiliser ce sous-domaine tel quel (recommandé — évite de le supprimer manuellement)",
    },
    "js_subdomain_used": {
        "en": "✗ {domain} already exists and hosts another app — choose another name (e.g. \"{suggestion}\").",
        "fr": "✗ {domain} existe déjà et héberge une autre app — choisis un autre nom (ex: \"{suggestion}\").",
    },
    "js_alert_subdomain_blocked": {
        "en": "This subdomain already hosts another app — choose another name before continuing.",
        "fr": "Ce sous-domaine héberge déjà une autre app — choisis un autre nom avant de continuer.",
    },
    "js_alert_path_blocked": {
        "en": "This address already hosts another app — choose another path before continuing.",
        "fr": "Cette adresse héberge déjà une autre app — choisis un autre chemin avant de continuer.",
    },

    # --- audit.html ---
    "title_audit": {"en": "Docker Gate — Residue audit", "fr": "Docker Gate — Audit des résidus"},
    "h1_audit": {"en": "Residue audit", "fr": "Audit des résidus"},
    "audit_lead": {
        "en": "Looking for anything Docker Gate might have left behind (forgotten tests, interrupted operations).",
        "fr": "Recherche de tout ce que Docker Gate aurait pu laisser traîner (tests oubliés, opérations interrompues).",
    },
    "h2_orphan_containers": {"en": "Orphan containers", "fr": "Conteneurs orphelins"},
    "no_orphan_containers": {"en": "No orphan container found.", "fr": "Aucun conteneur orphelin trouvé."},
    "h2_orphan_volumes": {"en": "Orphan data volumes", "fr": "Volumes de données orphelins"},
    "orphan_volumes_warning": {
        "en": "⚠️ May contain real data — remove one at a time, with full awareness.",
        "fr": "⚠️ Peuvent contenir de vraies données — à supprimer un par un, en connaissance de cause.",
    },
    "no_orphan_volumes": {"en": "No orphan volume found.", "fr": "Aucun volume orphelin trouvé."},
    "h2_dangling_images": {"en": "Unused Docker images", "fr": "Images Docker inutilisées"},
    "dangling_images_count": {"en": "{count} unused image(s)", "fr": "{count} image(s) inutilisée(s)"},
    "total_mb": {"en": "{mb} MB total", "fr": "{mb} Mo au total"},
    "btn_cleanup": {"en": "Clean up", "fr": "Nettoyer"},
    "no_dangling_images": {"en": "No unused image found.", "fr": "Aucune image inutilisée trouvée."},
    "h2_empty_domains": {"en": "Empty YunoHost domains", "fr": "Domaines YunoHost vides"},
    "empty_domains_help": {
        "en": "Reported only — never removed automatically, check and remove yourself if needed (Tools → Domains).",
        "fr": "Signalés uniquement — jamais supprimés automatiquement, à vérifier et retirer toi-même si besoin (Outils → Domaines).",
    },
    "no_empty_domains": {"en": "No empty domain found.", "fr": "Aucun domaine vide trouvé."},
    "btn_back": {"en": "← Back", "fr": "← Retour"},
    "confirm_delete_orphan_container": {"en": "Delete the orphan container {name}?", "fr": "Supprimer le conteneur orphelin {name} ?"},
    "confirm_delete_orphan_volume": {
        "en": "PERMANENTLY delete the volume {name} and all its data?",
        "fr": "Supprimer DÉFINITIVEMENT le volume {name} et toutes ses données ?",
    },

    # --- progress.html ---
    "title_progress": {"en": "Docker Gate — Installation in progress", "fr": "Docker Gate — Création en cours"},
    "h1_progress": {"en": "Installing \"{slug}\"…", "fr": "Création de \"{slug}\" en cours…"},
    "progress_lead": {
        "en": "This can take a few seconds to several minutes depending on the image and mode chosen — stay on this page.",
        "fr": "Ça peut prendre de quelques secondes à plusieurs minutes selon l'image et le mode choisi — reste sur cette page.",
    },
    "progress_not_found": {
        "en": "Progress tracking not found (the service may have restarted).",
        "fr": "Suivi introuvable (le service a peut-être redémarré).",
    },
    "summary_ok": {"en": "✓ Installation complete, nothing to watch out for.", "fr": "✓ Installation terminée, aucun point de vigilance."},
    "summary_warning_title": {"en": "⚠ Installation complete, with some points to check:", "fr": "⚠ Installation terminée, avec des points à vérifier :"},
    "btn_back_home": {"en": "← Back to home", "fr": "← Retour à l'accueil"},
}


def t(key, lang, **kwargs):
    """Traduit `key` dans `lang` (repli sur l'anglais puis sur la clé
    elle-même si absente — ne doit jamais planter sur une clé manquante)."""
    entry = STRINGS.get(key)
    if entry is None:
        return key
    template = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    return template.format(**kwargs) if kwargs else template


def normalize_lang(lang):
    """Ramène une valeur de langue quelconque (cookie, en-tête, réglage
    d'installation) à une langue supportée, repli sur l'anglais."""
    if lang and lang.lower() in LANGS:
        return lang.lower()
    return DEFAULT_LANG
