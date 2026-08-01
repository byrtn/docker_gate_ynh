# Changelog

All notable changes to Docker Gate are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to YunoHost's `version~ynhN` scheme (the part before
`~ynh` is the app's own version; `ynhN` increments for packaging-only changes
that don't touch the app's behavior).

## [1.5.1~ynh1] — 2026-08-01

### Fixed
- **Bug de multi-instance trouvé en préparant un protocole de test réel (jamais détecté par simple lecture de code)** : `install`/`upgrade`/`restore`/`remove` écrivaient tous en dur vers `/etc/sudoers.d/docker_gate` — un nom de fichier fixe, littéral, pas dérivé de `$app`. Le contenu du fichier était bien templaté par instance (`sed -i "s/__APP__/$app/g"`), mais la destination ne l'était pas. Conséquence concrète sur un serveur avec deux instances : la dernière installée/mise à jour écrase le fichier sudoers de l'autre, qui perd alors tout droit root — plus aucune action ne fonctionne pour elle (listage des domaines, création d'app...), échec silencieux en erreur 500 jamais expliqué avant ce diagnostic. Corrigé en utilisant `/etc/sudoers.d/$app` partout (chaque instance obtient enfin son propre fichier, cohérent avec son propre contenu).

## [1.5.0~ynh1] — 2026-07-31

### Added
- Bouton "Déconnexion" dans l'en-tête (icône + texte), trouvé manquant par Patrick en testant le multi-instance (fermer l'onglet laissait la session du domaine ouverte, sans aucun moyen de la clore proprement depuis l'app elle-même). Même endpoint que `wappos_portal_ynh` et le portail natif YunoHost (`/yunohost/portalapi/logout`, GET, appelé via `fetch`) — délègue entièrement la gestion de session à SSOwat, aucune logique de déconnexion réimplémentée nous-mêmes.

## [1.4.0~ynh1] — 2026-07-31

### Added
- **Support multi-instance** (`multi_instance = true`) — Docker Gate peut désormais être installée plusieurs fois sur le même serveur, sur des domaines différents, chaque instance gérant ses propres apps Docker de façon indépendante.
- `YNH_APP_ID` (variable d'environnement posée dans `conf/systemd.service` depuis la substitution `__APP__` de YunoHost) donne à chaque instance sa propre identité, utilisée pour préfixer tous les noms de ressources Docker qu'elle crée (`RESOURCE_PREFIX` dans `ynh_manager.py`) — conteneurs, volumes, réseaux. Le démon Docker est partagé par toutes les instances d'un même serveur et n'a lui-même aucune notion d'« instance » : sans ce préfixe, deux instances créant chacune une app du même nom entreraient en collision directe (même conteneur/volume/réseau).
- Les fonctions de détection et de suppression des résidus (page Audit — `find_orphan_*`/`remove_orphan_*`) sont désormais strictement bornées au préfixe de l'instance courante — sans quoi l'audit d'une instance aurait pu lister (et supprimer !) les conteneurs parfaitement sains d'une autre instance, simplement absents de son propre fichier d'état.

### Note opérationnelle importante
- **La désinstallation complète de Docker CE (page Audit) reste une action globale au serveur**, non isolée par instance : elle arrête et purge Docker entièrement, ce qui détruit aussi bien les apps de l'instance courante que celles de toute autre instance de Docker Gate installée sur le même serveur (ou tout autre conteneur Docker non lié à Docker Gate). L'avertissement déjà affiché à l'écran avant cette action ("détruit les conteneurs suivis ET les conteneurs étrangers, sans distinction") reste donc exact mais devient plus lourd de conséquences dès qu'il y a plusieurs instances — à garder en tête avant de cliquer depuis n'importe laquelle.
- Les apps Docker créées par une instance **avant** cette mise à jour gardent leur nom de conteneur/volume/réseau d'origine (stocké tel quel dans `data/apps.json`, jamais recalculé) — seules les nouvelles créations utilisent le nouveau schéma préfixé. Pour l'instance déjà installée aujourd'hui (id `docker_gate`), les futures créations porteront donc des noms du type `docker-gate-docker_gate-{slug}` (légèrement redondant mais sans impact fonctionnel) plutôt que l'ancien `docker-gate-{slug}`.

## [1.3.0~ynh1] — 2026-07-31

### Changed
- **Permission `main` revenue de `visitors` à `admins`** — Docker Gate est un outil réservé aux administrateurs, il ne doit jamais être accessible aux visiteurs anonymes ni à tous les comptes YunoHost, même via sa propre page de connexion. Le changement du 27/07 (voir 1.2.0~ynh1 ci-dessous) violait cette exigence produit et la convention native YunoHost pour les apps admin-only. SSOwat bloque de nouveau tout accès non-admin avant même que la requête n'atteigne l'app. Voir DECISIONS.md DEC-133 pour le détail complet, y compris la régression acceptée du bug de redirection post-connexion sur les domaines relayés (DEC-096) — trade-off explicitement assumé.
- `main.show_tile` remis à `false` dans le manifeste (le webadmin l'avait remis à `true` par défaut, désynchronisé de la réalité de production où il avait été repassé à `false` — voir DEC-097).
- `main.auth_header` repassé à `false` (plus utilisé, la vérification interne qui s'en servait a été retirée).

### Removed
- Page de connexion maison (`login.html`) et page d'accès refusé (`access_denied.html`) — plus nécessaires, SSOwat filtre désormais tout en amont.
- Le mécanisme de vérification interne (`portalapi/me`, relais du Basic-Auth) — devenu redondant.

## [1.2.0~ynh1] — 2026-07-27

### Changed
- **Permission `main` passée de `admins` à `visitors`** (publique) — l'accès admin réel est désormais vérifié en interne (`portalapi/me`, groupe `admins`), plus par SSOwat en amont. Corrige la boucle de redirection post-connexion cassée sur les domaines relayés (`dev.wappos.fr`) : un visiteur non authentifié voit maintenant la page de connexion de l'app directement, sans jamais transiter par le portail natif YunoHost (bug upstream non patchable, aucun hook JS par domaine n'existe côté YunoHost — voir DECISIONS.md DEC-096). Même pattern que `wappos_portail_ynh` (DEC-072).
- Version affichée en pied de page resynchronisée avec `manifest.toml` (dérive silencieuse trouvée en passant, `1.1.1` codé en dur alors que le manifest était déjà à `1.1.6~ynh1`).

### Added
- Page de connexion maison (`login.html`) et page d'accès refusé (`access_denied.html`), affichées respectivement à un visiteur non connecté et à un utilisateur connecté mais non-admin.

## [1.1.6~ynh1] — 2026-07-24

### Fixed
- Le formulaire d'ajout d'app ne présélectionnait jamais de domaine parent dans le menu déroulant — le navigateur retombait sur le premier domaine par ordre alphabétique de la liste YunoHost, sans lien avec le domaine réellement consulté (ex. app créée sous `byrtn.fr` au lieu de `wappos.fr`). Le formulaire présélectionne désormais `request.host`, tout en respectant un choix explicite de l'utilisateur en cas de nouvelle soumission après erreur.

## [1.1.5~ynh1] — 2026-07-22

### Changed
- "Souveraineté numérique" retirée du pied de page (demande de Patrick, alignement avec wappos-portail).

## [1.1.4~ynh1] — 2026-07-22

### Changed
- Le gros titre central "DOCKER GATE" (l'"eyebrow") est retiré pour aérer la page d'accueil. Le sous-titre "way to wappos" est déplacé sous le logo en haut à gauche (celui-ci passé en capitales), dans le même orange que l'ancien titre.

## [1.1.3~ynh1] — 2026-07-22

### Fixed
- **La police de marque BYRTN (Montserrat) est enfin réellement chargée** — elle était référencée en CSS (`font-family: 'Montserrat'`) depuis la toute première version, sans qu'aucun mécanisme (ni `@font-face`, ni lien Google Fonts) ne la charge jamais : l'app retombait silencieusement sur la police système depuis le début. Auto-hébergée (fichier variable `.woff2` unique, extrait de Google Fonts) plutôt que chargée depuis `fonts.googleapis.com`, cohérent avec le discours de souveraineté numérique. Rendu légèrement resserré (`letter-spacing: -0.015em`), demande de Patrick — pas de coupe "condensed" officielle pour Montserrat chez Google Fonts.

## [1.1.2~ynh1] — 2026-07-22

### Removed
- Le lien "Back to portal" (pointant en dur vers `/yunohost/sso/`) est retiré — devenu incohérent depuis que Docker Gate s'ouvre en nouvel onglet depuis wappos-portail (fermer l'onglet suffit).

## [1.1.1~ynh1] — 2026-07-20

### Changed
- **Multi-container creation/removal now goes through the real `docker compose` CLI** instead of a hand-rolled Docker SDK orchestration (network creation, per-container network aliasing, a bespoke 3-block rollback tree). Patrick's review after the first version shipped: that code reimplemented what Compose already does natively, with its own bug surface (two real bugs were found and fixed the same evening). A minimal, controlled `docker-compose.yml` is generated per app from the already-parsed fields only (image/port/volume/env — never the user's raw pasted text, a deliberate security boundary: `build`, `privileged`, `cap_add`, `devices`, `network_mode: host`, `secrets`, `extends` are never read by the parser, so they can never reach the generated file either). Every container/volume/network name stays forced to the exact `docker-gate-{slug}[-{service_key}]` convention the Audit page already expects — zero change there. Apps created before this change (e.g. pre-existing Portainer/Dashy) keep working through the old removal code, kept as a fallback path, no forced migration.
- `docker compose up -d --wait` now actually waits for containers to be healthy/running before exposing the app via YunoHost — the previous SDK-based flow never waited at all.
- `docker compose up --pull missing` replaces the hand-rolled "pull if missing" check (itself a same-day fix) — one less custom code path talking to the registry.

## [1.1.0~ynh1] — 2026-07-20

### Added
- **Multi-container mode (semi-piloted)**: pasting a docker-compose.yml
  that declares several services (e.g. an app + its database + a cache —
  Immich, Paperless-ngx...) no longer silently keeps only the first
  service. The Analyze step now lets you pick which service is exposed
  via YunoHost/SSO; every other service starts alongside it as an internal
  dependency, connected to a dedicated Docker network, with no published
  port and no SSO exposure. Each container (main and companions) is given
  a network alias equal to its own original compose service key, so env
  vars copied verbatim from the compose file (e.g.
  `DATABASE_URL=postgres://user:pass@db/db`) keep resolving correctly
  with zero rewriting. Removal cleans up the companions and the network
  the same way it already did for the main container/volume/domain.

### Fixed
- The Analyze step's `docker run`/docker-compose parser had 4 silent
  data-loss bugs, found while stress-testing it against real Docker Hub
  examples: a published port with a `/udp` or `/tcp` suffix (e.g.
  `-p 80:80/udp`) was kept as-is instead of the numeric port; a repeated
  `-p`/`-v` (or multiple `ports:`/`volumes:` entries) was silently
  overwritten/ignored instead of warning that only the first was kept;
  `${VAR}`/`${VAR:-default}` compose interpolation was never resolved (now
  resolved when a default is present, warned about otherwise); an
  `env_file:` reference was silently dropped with no indication its
  variables weren't picked up.

## [1.0.2~ynh1] — 2026-07-18

### Added
- The "Analyze" step now recognizes a short list of known SPA-type images
  (Portainer, Dashy, Heimdall, Homepage, Homarr, Organizr, Flame) and
  automatically pre-selects "dedicated subdomain" mode for them, instead of
  only showing generic help text and relying on the user to notice it.
  Found the hard way: Dashy was installed in "path" mode during a live
  screenshot session, resulting in a stuck loading screen (the exact same
  class of problem Portainer had hit earlier).

### Changed
- The self-signed-certificate warning shown after installing on a
  dedicated subdomain used to be one dense paragraph covering the DNS
  check, the TLS-passthrough/relay check, and the "just retry" tip all at
  once — easy to skim past. Split into 4 separate bullets (one per point)
  so each shows as its own line in the install summary. Prompted by a real
  troubleshooting session where the TLS-passthrough hint was in fact
  already present in the warning text, but got lost in the wall of text
  and only found much later.
- Version renumbered from `1.6~ynh4` down to `1.0.1~ynh1`, Patrick's
  decision right before submitting the app to the YunoHost community
  catalog: `1.6` felt presumptuous for a first public submission, so this
  moment is treated as the app's real "v1" instead. Purely a display
  change (manifest.toml, README badge, the footer version shown in the
  app itself) — no behavior difference. Historical entries below keep
  their original version numbers as an accurate record of what was true
  at the time, rather than being renumbered retroactively (same choice
  already made during the first versioning reset, see 1.0~ynh1 further
  down). Deployed via a clean uninstall/reinstall rather than
  `app upgrade` on the already-running instance, since YunoHost's upgrade
  path isn't meant to go to a lower version number.

## [1.6~ynh4] — 2026-07-18

### Fixed
- One more French comment (`# Durcissement de base`, no accented
  characters so it slipped past the earlier translation pass's grep) in
  `conf/systemd.service`, translated to English.
- `README.md`'s "testing branch" section (from the standard
  `readme_generator` template) linked to a `testing` branch that doesn't
  exist in this repo (single-branch `main` workflow) — a genuinely dead
  link (verified 404), removed rather than fabricating an unused branch
  just to make it resolve. Found during a full review of the published
  GitHub repo, requested by Patrick after catching the version badge issue
  above.

## [1.6~ynh3] — 2026-07-18

### Fixed
- `README.md`'s version badge was stuck at "0.2~ynh4" — never updated since
  the file was first auto-generated, well before the versioning scheme
  correction (see 1.0~ynh1 below). Found by Patrick while reviewing the
  published GitHub repo. Corrected to match `manifest.toml`; should go back
  to being auto-generated via `readme_generator` once the official tooling
  is used locally.

## [1.6~ynh2] — 2026-07-18

### Changed
- Translated all remaining French code comments and docstrings to English
  across `sources/*.py`, `scripts/*`, `conf/docker_gate.sudoers`,
  `manifest.toml`, and the HTML templates — packaging-only change, no
  behavior difference. The app's actual bilingual EN/FR user interface
  (`i18n.py`, `scripts/remove`'s interactive questions, `README_fr.md`,
  `doc/ADMIN_fr.md`) is untouched, as is the deliberately French-only
  footer tagline ("souveraineté numérique").

## [1.6~ynh1] — 2026-07-18

### Fixed
- Both the "Uninstall Docker CE" button (Audit page) and the interactive
  question in `scripts/remove` only warned about containers *not* managed
  by Docker Gate before offering to purge Docker CE — giving a false sense
  of safety whenever no such foreign container existed. In reality, purging
  Docker CE stops and destroys every container equally, including apps
  still tracked and kept on purpose (e.g. Portainer, kept when answering
  "no" to the child-apps removal question). Found by Patrick during a live
  GUI-based removal test: he correctly pointed out that removing Docker
  Gate without also removing Docker CE leaves child apps running and
  functional, but removing Docker CE afterwards (or in the same operation)
  would silently break them with no warning at all. Both warnings now cover
  all running containers, clearly distinguishing "still managed by Docker
  Gate" from "unrelated to Docker Gate".
- `scripts/remove`'s non-interactive messages (shown when Docker Gate is
  removed from the YunoHost admin panel — no terminal attached, so none of
  the interactive questions can ever appear) now explicitly explain the
  consequence and the correct order of operations: if Docker CE is also
  meant to be uninstalled, do it from the Audit page's "Uninstall Docker
  CE" button *before* removing Docker Gate itself — once Docker Gate is
  gone, that button (and any further warning about it) disappears with it.

## [1.5~ynh1] — 2026-07-18

### Added
- "Uninstall Docker CE" button on the Audit page (`/audit`): the interactive
  question in `scripts/remove` (see 1.4~ynh1 below) can never appear when
  Docker Gate is removed from the YunoHost admin panel instead of the command
  line — no terminal is attached in that case, so the safest default (leave
  Docker CE installed) always applies silently. This new button covers that
  gap: a genuine HTTP action, independent of how Docker Gate itself is
  removed. Same warning as the terminal question if a Docker container not
  managed by Docker Gate is still present, and the same two-click confirmation
  already used elsewhere on this page.

## [1.4~ynh1] — 2026-07-18

### Added
- `scripts/remove` now also asks (interactively, real terminal only) whether
  to fully uninstall Docker CE itself — symmetric to Docker Gate installing
  it automatically on first install. Warns explicitly if a Docker container
  not managed by Docker Gate is still running, since purging Docker CE would
  destroy it too, unrelated to this app. Same explicit yes/no mechanics as
  the existing child-apps removal question; never blocks outside a real
  terminal (Docker CE left installed by default in that case).

## [1.3~ynh1] — 2026-07-18

### Fixed
- False "Let's Encrypt certificate not obtained" warning when reusing an
  existing dedicated subdomain that already had a valid certificate:
  `yunohost domain cert install` exits non-zero when a valid certificate
  already exists (not an error in that case), but the warning was raised
  from that exit code alone, ignoring the real certificate status checked
  right after. Now based solely on the real check (`domain cert status`).
  Found while reinstalling Portainer as a Docker Gate child app on
  `portainer.wappos.fr`, a subdomain that already had a valid certificate.
- Removed the now-dead `warn_cert_not_obtained` i18n string (its content is
  already covered by `warn_cert_not_letsencrypt` for genuine failures).

## [1.2~ynh1] — 2026-07-18

### Fixed
- Fresh Docker CE installation was completely broken: `ynh_apt install
  --package="..."` is not valid syntax (`ynh_apt install` forwards its
  arguments straight to `apt-get install`, which has no `--package` option) —
  every install attempt on a machine without Docker already present crashed
  immediately. This had never been caught before because every previous test
  ran on a machine where Docker CE was already installed (the early-return
  guard in `ynh_docker_gate__ensure_docker_installed` skipped the broken code
  entirely). Found during a full from-scratch reinstall test (Docker CE
  purged beforehand on purpose). Fixed by passing the package list directly
  instead of through a nonexistent `--package=` flag.

## [1.1~ynh1] — 2026-07-18

### Added
- App version now shown in the footer.

### Changed
- Footer wording: "A BYRTN product" replaced by "Docker Gate v{version} ·
  © BYRTN" (real copyright sign instead of a plain dash standing in for
  one), tagline "souveraineté numérique" kept unchanged.

## [1.0~ynh1] — 2026-07-18

### Changed
- Version scheme corrected: `ynhN` had been misused since `0.2~ynh1` as a
  general iteration counter for every change (including real feature
  additions and bug fixes), instead of being reserved for packaging-only
  changes that don't touch the app's behavior (its intended meaning). Bumped
  to `1.0~ynh1` to reflect the app's actual maturity (audited, tested, ready
  for catalog submission) rather than reconstructing an artificial `0.3`
  through `0.9` history. From here on, any change to the app's behavior or
  appearance bumps the version before `~ynh`; only pure packaging fixes
  (sudoers paths, manifest fields, script logic with no user-visible effect)
  bump the `ynhN` counter alone.

## [0.2~ynh8] — 2026-07-18

### Fixed
- An app removed directly from the YunoHost admin panel (bypassing Docker
  Gate) kept showing up as a working app on the home page — the local
  bookkeeping file was never told the underlying YunoHost app/permission
  was gone. The app list is now reconciled against real YunoHost state on
  every page load: any tracked entry whose YunoHost app no longer exists
  is dropped from the bookkeeping file. Any leftover Docker container is
  then correctly picked up as an orphan on the Audit page instead of
  silently vanishing.

## [0.2~ynh7] — 2026-07-18

### Changed
- Tagline shortened from "the way to wappos" to "way to wappos".

## [0.2~ynh6] — 2026-07-18

### Changed
- "← Back to portal" link repositioned to the left of the EN | FR switcher
  (grouped together on the right side of the header, small gap between
  them) instead of centered between logo and language switcher.

## [0.2~ynh5] — 2026-07-18

### Added
- "← Back to portal" link in the header, pointing to the YunoHost SSO
  portal (`/yunohost/sso/`) — there was previously no way to leave Docker
  Gate and return to the portal from within the app itself.

## [0.2~ynh4] — 2026-07-17

### Fixed
- Tagline typo: "the way to wapp" corrected to "the way to wappos".

## [0.2~ynh3] — 2026-07-17

### Changed
- The "Docker Gate" title is rendered larger and more prominent again; the
  "the way to wapp" tagline underneath keeps its previous (smaller) size.

## [0.2~ynh2] — 2026-07-17

### Changed
- New logo artwork: the admin/portal logo (`logo.png`) and the logo applied
  to each exposed child app's tile (`sources/static/docker-gate-app-logo.png`)
  were redesigned.

## [0.2~ynh1] — 2026-07-17

Consolidates a full security/quality audit (8 workstreams) plus a real
`backup create`/`backup restore` cycle test — all found issues fixed and
verified on a live instance.

### Security
- Tightened sudoers rules: removed one dead rule (`app info *`), narrowed two
  overly broad rules (`app remove *` → `app remove redirect*`, and
  `user permission update *` → restricted to the fixed logo path — this one
  could previously change the permission group of *any* app on the server),
  removed 4 superfluous wildcards.

### Fixed
- `scripts/install`, `scripts/upgrade` and `scripts/restore` resolved package
  files (`conf/`, `sources/`, `logo.png`) via a relative path (`../conf/...`)
  that broke specifically during `yunohost backup restore` (different working
  directory than install/upgrade). Now resolved from the script's own real
  location, verified with an actual `backup create`/`app remove`/
  `backup restore` cycle.
- The safety guard that was supposed to block removal of Docker Gate while
  child apps still existed did not actually stop YunoHost's core resource
  deprovisioning (ports, permission, install dir) — only prevented cleanup by
  `scripts/remove` itself. Rewritten with an honest warning and full cleanup
  regardless of outcome.
- Orphaned Docker volume left behind when container creation succeeded but
  `containers.run()` failed right after.
- `data/apps.json` was not written atomically and had no recovery path from a
  corrupted file — a single bad write (full disk, interrupted process) could
  break the whole app. Now written via `tempfile` + `os.replace`; a corrupted
  file is renamed aside (`.corrupted-<timestamp>`) instead of crashing.
- Three routes (`/remove`, `/audit/remove_container`, `/audit/remove_volume`)
  had no generic error handling, unlike `/audit/prune_images`.
- The `/audit` page itself had no error isolation — a single failing check
  (e.g. `yunohost domain list` unavailable) crashed the whole page instead of
  showing a partial result with a warning.
- `scripts/remove`'s interactive removal-confirmation prompt (see Added,
  below) was only ever translated to French, unlike the rest of the app.

### Added
- Interactive prompt during `yunohost app remove docker_gate`: if child apps
  still exist, explicitly offers to remove them (and their data) too, instead
  of only warning. Requires an explicit yes/no answer (no implicit default on
  Enter).
- `LICENSE` now contains the full AGPL-3.0 text instead of a link only.
- `README.md`/`README_fr.md`, `doc/DESCRIPTION.md`/`DESCRIPTION_fr.md` for
  catalog packaging conformity (manifest validated against YunoHost's
  official JSON schema — 0 errors).

### Changed
- A conditional note now appears under the "clean up N orphaned resources"
  button on `/audit` when it doesn't cover everything it might sound like it
  covers (containers/images only, not volumes or empty domains).

---

## [0.1~ynh1] — 2026-07-15

Initial usable release: Docker CE auto-install, one-click container exposure
behind YunoHost SSO, orphan-resource audit page, EN/FR interface.
