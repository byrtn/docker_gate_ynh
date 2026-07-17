# Docker Gate — administration documentation

## What Docker Gate does

Docker Gate installs Docker CE on the YunoHost server (if needed) and lets you expose any Docker container behind YunoHost's single sign-on (SSO) with a single input — no need to ever write an nginx config or systemd file by hand.

Three ways to describe the app to install, detected automatically:
- a plain Docker image name (e.g. `vaultwarden/server:latest`) — the image is inspected to guess a default port and volume;
- a full `docker run ...` command (pasted as-is from a project's documentation);
- a `docker-compose.yml` file (pasted, imported as a file, or fetched from an `https://` URL).

Two exposure modes:
- **In a directory** (`domain.tld/path`) — the most common case, shares an existing domain.
- **On a dedicated subdomain** (`sub.domain.tld`) — needed for interfaces that don't work under a subpath (SPA-type interfaces like Portainer).

Each app can have persistent data (a named Docker volume, created automatically if a data path is provided) and its access set to one of YunoHost's 3 native groups: administrators only, all YunoHost accounts, or public.

## ⚠️ Important — what happens if you uninstall/reinstall Docker Gate while apps still exist?

**The Docker apps you created via Docker Gate are NOT deleted** if you uninstall Docker Gate itself (whether on purpose or during a cold reinstall) — their Docker container, their YunoHost exposure ("redirect" app, nginx config, SSO permission) remain fully intact and functional, completely independent of Docker Gate.

**But Docker Gate itself loses track of them.** Its home page will show "No app installed" even though containers it created are still running in the background — a real residue **from Docker Gate's point of view only**, not a failure of the apps themselves.

**How to find them again**: open Docker Gate's **Audit & cleanup** page after a reinstall — Docker containers named `docker-gate-<slug>` that are no longer in its state file show up as "orphan containers", detectable and removable (one by one) from that page.

**Caveat if you remove an orphan container found this way**: this stops the container, but the corresponding YunoHost "redirect" app (its portal tile, its nginx config) stays in place, now pointing at a stopped service (it will show an error when clicked). For a full cleanup, also remove that app from **Applications** in the YunoHost admin panel.

**Question asked at uninstall time (since 2026-07-17)**: if you uninstall Docker Gate from the command line (`yunohost app remove docker_gate`) while apps are still tracked, a question is shown directly in the terminal, in the app's current interface language (English or French, based on `data/default_language.txt` — the same setting changeable anytime from the EN/FR switcher in the app itself):
> *"Do you also want to remove the applications AND their data managed by Docker Gate? Answer explicitly 'yes' or 'no':"*

An **explicit** answer is required — a bare Enter or any other input loops back to the question ("Unrecognized answer") instead of silently choosing for you. Answering **yes** actually removes each app (Docker container, data volume, YunoHost exposure, dedicated domain if any) before continuing to uninstall Docker Gate itself — a genuine full cleanup in one go. Answering **no** leaves the apps untouched, exactly as described above (findable via `/audit` after a later reinstall). This question is only shown when a real terminal is attached (never during an automated/API removal — in that case, the safest default applies: nothing is touched).

<details>
<summary><strong>What Docker Gate does NOT do</strong></summary>

- **It does not back up or restore the containers/volumes/data of the apps it manages.** Docker Gate's YunoHost backup (`yunohost backup create`) only covers Docker Gate itself: its own files, its nginx/systemd configuration, its state file (`data/apps.json` — the list of apps it knows about). **No data from the Docker containers created through the interface is included.** Restoring a Docker Gate backup puts the tool back in place, with a state file referencing apps whose actual containers/volumes may have disappeared in the meantime if the disk was lost — not the services themselves.

  **This is a deliberate choice, not an oversight**: backing up the data of what Docker Gate hosts is a topic of its own (heterogeneous data formats depending on the app, potentially large volumes, backup frequency varying with each app's criticality) that goes beyond the scope of an installation tool. **It is the server administrator's responsibility to plan their own backup strategy** for the containers/volumes they create through this tool (e.g. backing up Docker volumes with a dedicated tool, disk snapshots, etc.).

  *BYRTN internal note: a broader backup tool is planned separately (the "Vaultn" project) — Docker Gate does not anticipate this piece, it deliberately stays simple and focuses on installation/exposure, not data protection.*

- **It does not automatically sync an external relay/reverse-proxy.** In "dedicated subdomain" mode, if the YunoHost server itself sits behind a TLS-passthrough relay (2-server topology), Docker Gate cannot configure that relay (out of its scope — it only knows the machine it's installed on). A non-blocking warning flags this at the end of installation if the Let's Encrypt certificate could not be obtained.

- **It does not manage a centralized, multi-tool port registry.** The `9100-9999` range is its own; it avoids collisions with its own apps and with existing Docker containers, but has no knowledge of ports possibly reserved by other tools on the server.

</details>

<details>
<summary><strong>How it works (architecture)</strong></summary>

- **Backend**: Flask + gunicorn (single worker — progress tracking lives in Python memory, see `progress.py`), dedicated system user, member of the `docker` group.
- **Elevated rights**: a targeted sudoers file (`conf/docker_gate.sudoers`) authorizes only the necessary `yunohost app/domain/diagnosis` commands — never generic sudo. This file is (re)deployed on install, upgrade, **and restore**.
- **State**: each created app is recorded in `data/apps.json` (slug, image, ports, domain/path, optional volume). This is Docker Gate's only source of truth about what it manages — a Docker container that exists but doesn't appear in this file is treated as a residue (see the Audit page).
- **Exposure**: each Docker app is exposed via the official YunoHost "redirect" app in reverse-proxy mode towards `127.0.0.1:<port>` — so SSOwat and nginx (YunoHost's standard mechanism) handle authentication and TLS, not Docker Gate itself.
- **Removal (of a child app)**: done in 3 separately-verified layers (SSO permission + nginx config, Docker container, state entry) — each step is attempted independently; a failure on one step never blocks the next ones, and the entry is always removed from the state at the end (a real residue stays detectable via the Audit page rather than blocking indefinitely).
- **Audit & cleanup**: detects containers/volumes/images/domains left behind by an interrupted attempt. Volumes are never bulk-deleted (may contain real data) — one at a time, with explicit confirmation.
- **Removing Docker Gate itself** (not a child app): see the "⚠️ Important" box at the top of this document — a warning is shown if apps are still tracked, but it does not prevent the removal from proceeding (a YunoHost core limitation, not this package's).
- **Application security**: CSRF token (signed Flask session) on every action that changes real state; session key generated randomly at install time (never hard-coded in the source).

</details>

<details>
<summary><strong>Known limitations (backlog, not bugs)</strong></summary>

- Both "path" and "dedicated subdomain" modes have a preventive address-collision check before creation (parity ensured since 2026-07-15).
- Docker images on a private registry with an explicit port in the name (e.g. `registry.example.com:5000/image:tag`) are not recognized by the automatic parser — enter them in advanced mode instead.
- One YunoHost server at a time: `multi_instance = false` in the manifest — only one Docker Gate installation per server (the Docker apps it manages are not subject to this limit).

</details>
