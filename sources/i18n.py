"""
Docker Gate — FR/EN internationalization.

Deliberately lightweight mechanism (a Python dict, no .po/.mo compilation)
rather than Flask-Babel — consistent with the rest of the project's
minimalist style, and enough for this app's volume of text.

English by default (consistent with the upcoming public release), French
selectable from the interface (see /set_language in app.py) and right from
install (see manifest.toml, default_language question).

Each key carries the text for both languages. Parameterized messages use
the `.format(**kwargs)` syntax (e.g. "{domain}").
"""

DEFAULT_LANG = "en"
LANGS = ("en", "fr")

STRINGS = {
    # --- Progress steps (stable keys, never displayed as-is —
    # see build_create_steps in ynh_manager.py and progress.html) ---
    "step_check_params": {"en": "Checking parameters", "fr": "Vérification des paramètres"},
    "step_pick_port": {"en": "Selecting a free port", "fr": "Sélection d'un port libre"},
    "step_create_domain": {"en": "Creating the YunoHost domain", "fr": "Création du domaine YunoHost"},
    "step_dns_diag": {"en": "DNS diagnosis", "fr": "Diagnostic DNS"},
    "step_web_diag": {"en": "Web diagnosis", "fr": "Diagnostic Web"},
    "step_get_cert": {"en": "Obtaining the Let's Encrypt certificate", "fr": "Obtention du certificat Let's Encrypt"},
    "step_check_cert": {"en": "Checking the obtained certificate", "fr": "Vérification du certificat obtenu"},
    "step_write_compose": {"en": "Preparing the container configuration", "fr": "Préparation de la configuration des conteneurs"},
    "step_compose_up": {"en": "Starting the Docker container(s)", "fr": "Démarrage du/des conteneur(s) Docker"},
    "step_expose_app": {"en": "Exposing via YunoHost (nginx + SSO)", "fr": "Exposition via YunoHost (nginx + SSO)"},

    # --- Errors / warnings (ynh_manager.py) ---
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
    "err_docker_run_duplicate_port": {
        "en": "This command publishes more than one port — only the first one was kept, check the others manually.",
        "fr": "Cette commande publie plusieurs ports — seul le premier a été retenu, vérifiez les autres manuellement.",
    },
    "err_docker_run_duplicate_volume": {
        "en": "This command mounts more than one volume — only the first one was kept, check the others manually.",
        "fr": "Cette commande monte plusieurs volumes — seul le premier a été retenu, vérifiez les autres manuellement.",
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
    "err_compose_unresolved_vars": {
        "en": "This docker-compose.yml uses variable(s) without a default value ({vars}) — fill in the affected field(s) by hand.",
        "fr": "Ce docker-compose.yml utilise des variables sans valeur par défaut ({vars}) — complétez le(s) champ(s) concerné(s) à la main.",
    },
    "info_secrets_autogenerated": {
        "en": "Strong random values were generated automatically for: {list}. Review them below and change them if you need specific values.",
        "fr": "Des valeurs aléatoires robustes ont été générées automatiquement pour : {list}. Vérifie-les ci-dessous et modifie-les si tu as besoin de valeurs précises.",
    },
    "err_compose_env_file_not_supported": {
        "en": "This service uses 'env_file' — variables from that file aren't read automatically, add them manually if needed.",
        "fr": "Ce service utilise 'env_file' — les variables de ce fichier ne sont pas lues automatiquement, ajoutez-les manuellement si besoin.",
    },
    "err_compose_multiple_ports": {
        "en": "This service declares more than one port — only the first one was kept, check the others manually.",
        "fr": "Ce service déclare plusieurs ports — seul le premier a été retenu, vérifiez les autres manuellement.",
    },
    "err_compose_multiple_volumes": {
        "en": "This service declares more than one data volume — only the first one was kept, check the others manually.",
        "fr": "Ce service déclare plusieurs volumes de données — seul le premier a été retenu, vérifiez les autres manuellement.",
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
            "but visitors will see a security warning in their browser in the meantime. Request the certificate "
            "again from the YunoHost admin panel (Domains > {domain} > Certificate) once you've checked the points "
            "below."
        ),
        "fr": (
            "{domain} n'a pour l'instant qu'un certificat {ca_type} (pas encore Let's Encrypt) — l'app fonctionne "
            "déjà, mais les visiteurs verront un avertissement de sécurité dans leur navigateur en attendant. "
            "Redemande le certificat depuis l'admin YunoHost (Domaines > {domain} > Certificat) une fois les points "
            "ci-dessous vérifiés."
        ),
    },
    # Split into its own bullet (2026-07-18, Patrick's feedback after a
    # real TLS-passthrough troubleshooting session) — these two checks
    # used to be buried in one dense paragraph together with
    # warn_cert_not_letsencrypt above; each now becomes its own list item
    # in the install summary (see progress.html, one <li> per warning
    # string) so neither gets skipped over.
    "warn_cert_check_dns": {
        "en": "→ Check that your DNS zone is properly configured with your registrar for {domain}.",
        "fr": "→ Vérifie que ta zone DNS est bien configurée chez ton registrar pour {domain}.",
    },
    "warn_cert_check_passthrough": {
        "en": (
            "→ If this server is behind a relay/reverse-proxy (TLS-passthrough, multi-server setup), check that "
            "{domain} is explicitly declared there too — otherwise Let's Encrypt validation can never reach this "
            "server, no matter how many times you retry."
        ),
        "fr": (
            "→ Si ce serveur est derrière un relais/reverse-proxy (TLS-passthrough, architecture multi-serveurs), "
            "vérifie que {domain} y est aussi explicitement déclaré — sans ça, la validation Let's Encrypt ne peut "
            "jamais atteindre ce serveur, quel que soit le nombre de tentatives."
        ),
    },
    "warn_cert_retry_tip": {
        "en": "→ If everything above was already fine, a simple retry is usually enough (YunoHost sometimes blocks the very first attempt on a freshly created domain).",
        "fr": "→ Si tout ce qui précède était déjà bon, un simple nouvel essai suffit généralement (YunoHost bloque parfois le tout premier essai sur un domaine tout juste créé).",
    },
    "err_write_compose": {
        "en": "Unable to write the container configuration to disk: {error}",
        "fr": "Impossible d'écrire la configuration des conteneurs sur le disque : {error}",
    },
    "err_compose_config_invalid": {
        "en": "The generated container configuration is invalid — this is a Docker Gate bug, please report it.",
        "fr": "La configuration des conteneurs générée est invalide — c'est un bug de Docker Gate, merci de le signaler.",
    },
    "err_compose_up_failed": {
        "en": "Docker was unable to start the container(s).",
        "fr": "Docker n'a pas pu démarrer le(s) conteneur(s).",
    },
    "err_compose_down_failed": {
        "en": "Unable to stop/remove the container(s).",
        "fr": "Impossible d'arrêter/supprimer le(s) conteneur(s).",
    },
    "err_expose_app": {
        "en": "Exposing via the YunoHost 'redirect' app failed. The Docker container was started but isn't exposed yet.",
        "fr": "L'exposition via l'app YunoHost 'redirect' a échoué. Le conteneur Docker a été lancé mais n'est pas encore exposé.",
    },
    "err_apply_child_logo_admin": {
        "en": "Unable to apply the Docker Gate icon in the admin panel.",
        "fr": "Impossible d'appliquer l'icône Docker Gate dans le panneau d'administration.",
    },
    "err_apply_child_logo_portal": {
        "en": "Unable to apply the Docker Gate icon on the user portal tile.",
        "fr": "Impossible d'appliquer l'icône Docker Gate sur la tuile du portail utilisateur.",
    },
    "warn_child_logo_admin_failed": {
        "en": "The app was exposed successfully, but the Docker Gate icon could not be applied in the admin panel: {error}",
        "fr": "L'app a bien été exposée, mais l'icône Docker Gate n'a pas pu être appliquée dans le panneau d'administration : {error}",
    },
    "warn_child_logo_portal_failed": {
        "en": "The app was exposed successfully, but the Docker Gate icon could not be applied on the user portal tile: {error}",
        "fr": "L'app a bien été exposée, mais l'icône Docker Gate n'a pas pu être appliquée sur la tuile du portail utilisateur : {error}",
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
    "err_remove_companion_container": {
        "en": "Unable to remove the internal dependency container '{name}': {error}",
        "fr": "Impossible de supprimer le conteneur de la dépendance interne '{name}' : {error}",
    },
    "err_remove_companion_volume": {
        "en": "Unable to remove the internal dependency's volume '{name}': {error}",
        "fr": "Impossible de supprimer le volume de la dépendance interne '{name}' : {error}",
    },
    "err_remove_network": {
        "en": "Unable to remove the app's dedicated Docker network '{name}': {error}",
        "fr": "Impossible de supprimer le réseau Docker dédié de l'app '{name}' : {error}",
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
    "err_network_not_orphan": {
        "en": "This network isn't recognized as an orphan, removal refused for safety.",
        "fr": "Ce réseau n'est pas reconnu comme orphelin, suppression refusée par sécurité.",
    },
    "err_docker_ce_stop": {
        "en": "Unable to stop the Docker services.",
        "fr": "Impossible d'arrêter les services Docker.",
    },
    "err_docker_ce_purge": {
        "en": "Unable to remove the Docker CE packages.",
        "fr": "Impossible de supprimer les paquets Docker CE.",
    },
    "err_docker_ce_autoremove": {
        "en": "Unable to clean up unused dependencies.",
        "fr": "Impossible de nettoyer les dépendances devenues inutiles.",
    },
    "err_docker_ce_rm": {
        "en": "Unable to remove some Docker CE files/directories.",
        "fr": "Impossible de supprimer certains fichiers/répertoires de Docker CE.",
    },
    "err_docker_ce_groupdel": {
        "en": "Unable to remove the 'docker' system group.",
        "fr": "Impossible de supprimer le groupe système 'docker'.",
    },

    # --- app.py (flash messages) ---
    "flash_app_removed": {"en": "App '{slug}' removed.", "fr": "App '{slug}' supprimée."},
    "flash_data_removed": {"en": "Data also removed.", "fr": "Données également supprimées."},
    "flash_data_kept": {"en": "Data kept.", "fr": "Données conservées."},
    "flash_domain_removed": {"en": "YunoHost domain also removed.", "fr": "Domaine YunoHost également supprimé."},
    "flash_orphan_container_removed": {"en": "Orphan container '{name}' removed.", "fr": "Conteneur orphelin '{name}' supprimé."},
    "flash_orphan_volume_removed": {"en": "Orphan volume '{name}' removed.", "fr": "Volume orphelin '{name}' supprimé."},
    "flash_orphan_network_removed": {"en": "Orphan network '{name}' removed.", "fr": "Réseau orphelin '{name}' supprimé."},
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
    "flash_docker_ce_uninstalled": {
        "en": "Docker CE has been fully uninstalled from this server.",
        "fr": "Docker CE a été entièrement désinstallé de ce serveur.",
    },

    # --- Templates: shared ---
    "btn_confirm": {"en": "Confirm?", "fr": "Confirmer ?"},
    # Note: the footer "A BYRTN product — digital sovereignty." deliberately
    # stays ALWAYS in French, in both languages (explicit request from
    # Patrick, 2026-07-15) — hardcoded in base.html, not a translation key
    # here.
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
    "users_label": {"en": "restricted (users)", "fr": "restreint (utilisateurs)"},
    "persistent_data_suffix": {"en": " — persistent data", "fr": " — données persistantes"},
    "companions_summary": {
        "en": "+ {count} internal service(s): {names}",
        "fr": "+ {count} service(s) interne(s) : {names}",
    },
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
    # YunoHost's native 3-group permission model (audit 2026-07-17,
    # docs/02-wappos/audits/2026-07-17-audit-permissions-yunohost.md) — the
    # 3 options map 1:1 to the real admins/all_users/visitors groups, no
    # custom reinvention.
    "visibility_field_label": {"en": "Access", "fr": "Accès"},
    "visibility_option_admins": {"en": "Administrators only (default)", "fr": "Administrateurs uniquement (par défaut)"},
    "visibility_option_users": {"en": "All YunoHost accounts", "fr": "Tous les comptes YunoHost"},
    "visibility_option_public": {"en": "Public (anyone with the link)", "fr": "Public (toute personne connaissant le lien)"},
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
    "js_spa_mode_suggested": {
        "en": "⚠️ This image is known not to work under a subpath — \"dedicated subdomain\" mode has been pre-selected for you.",
        "fr": "⚠️ Cette image est connue pour ne pas fonctionner sous un sous-chemin — le mode \"sous-domaine dédié\" a été présélectionné pour toi.",
    },
    "js_comm_error": {"en": "Communication error with the server.", "fr": "Erreur de communication avec le serveur."},
    "js_multi_service_prompt": {
        "en": "This docker-compose.yml declares several services — pick the one to expose via YunoHost/SSO. The others will run alongside it as internal dependencies (database, cache...), not publicly reachable.",
        "fr": "Ce docker-compose.yml déclare plusieurs services — choisis celui à exposer via YunoHost/SSO. Les autres démarreront à ses côtés comme dépendances internes (base de données, cache...), non accessibles publiquement.",
    },
    "js_companions_summary": {
        "en": "Will also start as internal dependencies (not exposed): {list}.",
        "fr": "Démarreront aussi comme dépendances internes (non exposés) : {list}.",
    },
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
    "h2_orphan_networks": {"en": "Orphan networks", "fr": "Réseaux orphelins"},
    "no_orphan_networks": {"en": "No orphan network found.", "fr": "Aucun réseau orphelin trouvé."},
    "confirm_delete_orphan_network": {"en": "Delete the orphan network {name}?", "fr": "Supprimer le réseau orphelin {name} ?"},
    "h2_dangling_images": {"en": "Unused Docker images", "fr": "Images Docker inutilisées"},
    "dangling_images_count": {"en": "{count} unused image(s)", "fr": "{count} image(s) inutilisée(s)"},
    "total_mb": {"en": "{mb} MB total", "fr": "{mb} Mo au total"},
    "btn_cleanup": {"en": "Clean up", "fr": "Nettoyer"},
    "btn_cleanup_all": {
        "en": "Clean up {n} detected leftover{plural}",
        "fr": "Nettoyer {n} résidu{plural} détecté{plural}",
    },
    # Audit workstream 4 (2026-07-17): this bulk button never counts or
    # touches volumes or empty domains (see comment in audit.html) —
    # without this note, nothing on screen signaled that, risking the
    # belief that "everything" is cleaned up when 2 out of 4 categories are
    # never handled by this button.
    "bulk_cleanup_scope_note": {
        "en": "Containers and images only — volumes, networks, and empty domains are always handled one at a time, below.",
        "fr": "Conteneurs et images uniquement — les volumes, réseaux et domaines vides se traitent toujours un par un, ci-dessous.",
    },
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
    "h2_docker_ce": {"en": "Docker CE (the server's Docker engine)", "fr": "Docker CE (le moteur Docker du serveur)"},
    "docker_ce_installed": {"en": "Installed on this server.", "fr": "Installé sur ce serveur."},
    "docker_ce_not_installed": {"en": "Not installed on this server.", "fr": "Non installé sur ce serveur."},
    "docker_ce_tracked_warning": {
        "en": (
            "⚠️ {count} app(s) managed by Docker Gate are still running on this server ({names}) — "
            "uninstalling Docker CE will stop them too, and they won't work again until Docker CE is "
            "reinstalled. Consider removing these apps first if you don't want to keep them."
        ),
        "fr": (
            "⚠️ {count} app(s) gérées par Docker Gate tournent encore sur ce serveur ({names}) — "
            "désinstaller Docker CE les arrêtera aussi, et elles ne fonctionneront plus tant que Docker "
            "CE n'est pas réinstallé. Envisage de supprimer ces apps d'abord si tu ne comptes pas les garder."
        ),
    },
    "docker_ce_foreign_warning": {
        "en": (
            "⚠️ {count} container(s) not managed by Docker Gate are still present on this server "
            "({names}) — uninstalling Docker CE will destroy them too, unrelated to Docker Gate."
        ),
        "fr": (
            "⚠️ {count} conteneur(s) non gérés par Docker Gate sont encore présents sur ce serveur "
            "({names}) — désinstaller Docker CE les détruira aussi, sans rapport avec Docker Gate."
        ),
    },
    "btn_uninstall_docker_ce": {"en": "Uninstall Docker CE", "fr": "Désinstaller Docker CE"},
    "confirm_uninstall_docker_ce": {
        "en": "PERMANENTLY uninstall Docker CE (packages, /var/lib/docker, docker group) from this server?",
        "fr": "Désinstaller DÉFINITIVEMENT Docker CE (paquets, /var/lib/docker, groupe docker) de ce serveur ?",
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

    # --- base.html (header) ---
    "nav_back_portal": {"en": "← Back to portal", "fr": "← Retour au portail"},
}


def t(key, lang, **kwargs):
    """Translates `key` into `lang` (falls back to English, then to the key
    itself if missing — must never crash on a missing key)."""
    entry = STRINGS.get(key)
    if entry is None:
        return key
    template = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    return template.format(**kwargs) if kwargs else template


def normalize_lang(lang):
    """Brings any language value (cookie, header, install setting) back to
    a supported language, falling back to English."""
    if lang and lang.lower() in LANGS:
        return lang.lower()
    return DEFAULT_LANG
