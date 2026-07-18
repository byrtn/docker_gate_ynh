# Changelog

All notable changes to Docker Gate are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to YunoHost's `version~ynhN` scheme (the part before
`~ynh` is the app's own version; `ynhN` increments for packaging-only changes
that don't touch the app's behavior).

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
