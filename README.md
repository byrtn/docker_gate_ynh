<!--
N.B. (audit chantier 6, 17/07/2026) : sur une app YunoHost officielle, ce
fichier est normalement AUTO-GÉNÉRÉ par https://github.com/YunoHost/apps/tree/main/tools/readme_generator
à partir de manifest.toml + doc/DESCRIPTION*.md + doc/screenshots/, et ne
doit JAMAIS être édité à la main une fois généré. Celui-ci est un brouillon
manuel provisoire (le dépôt n'est pas encore public/soumis au catalogue) —
à remplacer par la vraie sortie de cet outil avant toute soumission
officielle, une fois doc/screenshots/ rempli de vraies captures.
-->

# Docker Gate for YunoHost

[![Integration level](https://dash.yunohost.org/integration/docker_gate.svg)](https://dash.yunohost.org/appci/app/docker_gate)
[![Install Docker Gate with YunoHost](https://install-app.yunohost.org/install-with-yunohost.svg)](https://install-app.yunohost.org/?app=docker_gate)

*[Lire ce README en français.](./README_fr.md)*

## Overview

Docker Gate installs Docker CE on the YunoHost server (if needed) and lets you expose any Docker container behind YunoHost's single sign-on (SSO) with a single input — no need to ever write an nginx config or systemd file by hand.

Three ways to describe the app to install, detected automatically:
- a plain Docker image name (e.g. `vaultwarden/server:latest`);
- a full `docker run ...` command (pasted as-is from a project's documentation);
- a `docker-compose.yml` file (pasted, imported as a file, or fetched from an `https://` URL).

Two exposure modes (in a directory, or on a dedicated subdomain), persistent data volumes, and access control set to one of YunoHost's 3 native groups (administrators only, all YunoHost accounts, or public).

**Shipped in : 0.1~ynh1**

## Documentation and resources

* Official app website: *not yet published — planned before catalog submission*
* Admin documentation (English): [doc/ADMIN.md](./doc/ADMIN.md)
* Documentation admin (français) : [doc/ADMIN_fr.md](./doc/ADMIN_fr.md)
* Upstream app code repository: [github.com/byrtn/docker_gate_ynh](https://github.com/byrtn/docker_gate_ynh)
* YunoHost documentation for this app: *not yet submitted to the official catalog*
* Report a bug: [github.com/byrtn/docker_gate_ynh/issues](https://github.com/byrtn/docker_gate_ynh/issues)

## Developer info

Please send your pull request to the [main branch](https://github.com/byrtn/docker_gate_ynh/tree/main).

To try the package before it's merged, you can run:

```bash
sudo yunohost app install https://github.com/byrtn/docker_gate_ynh/tree/main --debug
```

Or, if the code currently lives in the `byrtn-homelab` monorepo (not yet migrated to its own dedicated repository — see the open question tracked in `docs/TODO-PROCHAINE-SESSION.md`):

```bash
sudo yunohost app install /path/to/docs/02-wappos/docker_gate_ynh --debug
```

As for other dev-related instructions, please refer to the [official packaging documentation](https://yunohost.org/packaging_apps).
