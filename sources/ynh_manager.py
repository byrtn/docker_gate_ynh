"""
Docker Gate — Docker + YunoHost management module.

Step 2 (2026-07-11): the real logic for creating/removing Docker apps
exposed behind YunoHost, in both modes (path and dedicated subdomain).

Security principle (see manifest.toml + conf/docker_gate.sudoers): this
module runs under a restricted system user. The only privileged commands
(yunohost app install/remove, domain add/cert install) go through
`sudo -n`, narrowly authorized by the sudoers file laid down at install
time — never generic sudo.

Internationalization (2026-07-15): all user-facing messages (errors,
warnings) go through `i18n.t(key, lang, **kwargs)` — `lang` is an explicit
parameter of every function rather than implicit Flask context, so this
module stays testable independently of Flask and to correctly handle the
case of a creation launched as a background task (a thread separate from
the original HTTP request, see app.py): the user's language is captured
before the thread starts, never inferred afterwards.
"""
import json
import os
import re
import secrets
import shlex
import shutil
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

# Known SPA-type (Single Page Application) images that don't work when
# exposed under a subpath — added 2026-07-18 after a real installation
# mistake (Dashy installed in "path" mode, stuck on a blank loading screen)
# that repeated a problem already known from Portainer (see mode_help in
# i18n.py). The existing help text only warns generically; this list lets
# the interface proactively pre-select "dedicated subdomain" mode instead
# of relying on the user noticing and reading that text. Best-effort,
# substring match against the image name — not exhaustive, new entries can
# be added here as they're found.
KNOWN_SPA_IMAGES = (
    "portainer",
    "dashy",
    "heimdall",
    "homepage",
    "homarr",
    "organizr",
    "flame",
)


def _looks_like_spa(image):
    if not image:
        return False
    image_lower = image.lower()
    return any(name in image_lower for name in KNOWN_SPA_IMAGES)

# Logo applied to every container exposed via "redirect" (workstream 1,
# 2026-07-16) — same 2 YunoHost mechanisms as for Docker Gate itself (see
# scripts/install), applied here to the created "redirect" instance.
CHILD_LOGO_SOURCE = Path(__file__).parent / "static" / "docker-gate-app-logo.png"

docker_client = docker.from_env()


class DockerConnectorError(Exception):
    """Readable business-logic error, shown as-is to the user."""


def _load_state():
    """Audit workstream 5 (2026-07-17, edge cases): before this fix, a
    corrupted `data/apps.json` (write interrupted by a full disk, a crash,
    or a failed manual edit) crashed the WHOLE interface (every route calls
    this function). An unreadable file is now set aside (never deleted —
    kept for investigation/manual recovery) and replaced with an empty
    state, so the app stays usable instead of fully unavailable."""
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
    """Atomic write (audit workstream 5, 2026-07-17): writes to a temporary
    file then `os.replace()` (atomic rename on the same filesystem) rather
    than writing directly into `apps.json` — an interruption mid-write
    (crash, full disk) can no longer leave a half-written, and therefore
    invalid, file for `_load_state()`."""
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
    # Backward compatibility (audit 2026-07-17): apps created before the
    # switch to the 3-group model only have a "public" boolean on disk —
    # inferred here on read, never rewritten, real behavior unchanged for
    # these existing apps.
    for a in apps:
        if "visibility" not in a:
            a["visibility"] = "visitors" if a.get("public") else "admins"

    # Reconciliation with real YunoHost state (bug found on 2026-07-18): if
    # a child app is removed directly from the YunoHost admin panel
    # (bypassing Docker Gate), our state file never finds out on its own
    # and kept showing it as functional even though its SSO
    # permission/nginx config no longer exists. Checked on every page
    # load: any entry whose yunohost_app_id no longer matches a real
    # YunoHost app is dropped from the state — the remaining Docker
    # container (if any) becomes detectable again as residue via /audit,
    # which already knows how to handle it properly. No data is lost
    # here: only the now-wrong tracking is fixed, the actual removal of
    # the container/volume remains subject to the same safeguards as usual
    # (Audit & cleanup page).
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
        # Best-effort: if the check fails (sudo, invalid JSON...), show the
        # state as-is rather than breaking the home page.
        pass

    return apps


def _slug_is_valid(slug):
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{1,30}", slug))


def _slug_already_used(slug):
    return any(a["slug"] == slug for a in _load_state())


def _pick_free_port(lang):
    """Picks a free port in the 9100-9999 range, checking both our state
    file AND the ports actually used by Docker (to never collide with a
    manually installed app, like Portainer on 9101)."""
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
    """Runs a sudo -n (non-interactive) command, authorized by the sealed
    sudoers file. Raises DockerConnectorError with a readable message on
    failure, rather than letting a raw trace leak onto the screen."""
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
    """Lists domains already known to YunoHost (to populate the dropdown
    for the 'path' mode)."""
    output = _run_sudo(
        ["yunohost", "domain", "list", "--output-as", "json"],
        t("err_list_domains", lang),
        lang,
    )
    data = json.loads(output)
    return data.get("domains", [])


def fetch_compose_from_url(url, lang):
    """Fetches the content of a docker-compose.yml from a URL provided by
    the user (e.g. a raw GitHub link). Restricted to https:// — this app
    already has elevated rights on the server (targeted sudo), so the
    marginal risk of an outgoing request adds nothing new, but plain
    http:// is refused anyway as basic hygiene."""
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


_ENV_EXAMPLE_CANDIDATES = (".env.example", "example.env", ".env.sample", "env.example", ".env.dist", ".env.template")


def fetch_env_example_from_url(compose_url, lang):
    """Best-effort: looks for a sibling env-example file next to a
    docker-compose.yml fetched by URL (same directory, common naming
    conventions) and returns its raw text, or None if none is found.

    Deliberately mechanical only, no per-app knowledge of ours (Patrick,
    2026-07-20: "je ne veux pas maintenir un catalogue d'applications" —
    Docker Hub already is one, and most real projects already publish an
    example env file right next to their compose, e.g. Immich's
    docker/example.env alongside docker/docker-compose.yml). We only ever
    read what the upstream project already publishes, exactly the way a
    human would open both files side by side — never our own data.

    Never raises: a missing/unreachable example file is a normal case
    (many projects don't have one, or don't use env_file: at all), not a
    failure — the existing "add these variables manually" warning stays
    the fallback."""
    if not compose_url.startswith("https://"):
        return None
    base = compose_url.rsplit("/", 1)[0] + "/"
    for name in _ENV_EXAMPLE_CANDIDATES:
        try:
            response = requests.get(base + name, timeout=5)
        except requests.RequestException:
            continue
        if response.status_code == 200 and 0 < len(response.content) <= 50_000 and response.text.strip():
            return response.text
    return None


def inspect_docker_image(image_name, lang):
    """Downloads (if needed) and inspects a Docker image to automatically
    guess its default port and volume, when the user only gives an image
    name (the least informative of the three accepted formats).
    Best-effort: many images don't declare this information in their
    metadata (only in their free-text documentation) — in that case only
    what could be found is filled in, never a made-up value."""
    try:
        image = docker_client.images.pull(image_name)
    except docker.errors.APIError as e:
        raise DockerConnectorError(t("err_pull_image", lang, image=image_name, error=e))

    config = image.attrs.get("Config", {}) or {}
    result = {"image": image_name, "container_port": None, "data_path": None, "suggested_slug": None}

    exposed_ports = config.get("ExposedPorts") or {}
    if exposed_ports:
        # Docker format: {"80/tcp": {}, "443/tcp": {}} — take the first one.
        first_port = next(iter(exposed_ports))
        result["container_port"] = _strip_port_protocol(first_port)

    volumes = config.get("Volumes") or {}
    if volumes:
        # Docker format: {"/data": {}} — take the first one declared.
        result["data_path"] = next(iter(volumes))

    return result


def _strip_port_protocol(port_str):
    """'80/udp' -> '80'. Docker accepts a '/udp' or '/tcp' suffix on
    published ports (both in `docker run -p` and in a compose `ports:`
    entry) — without stripping it, the port ends up stored as a
    non-numeric string and breaks downstream validation (err_port_not_a_number)."""
    return port_str.split("/")[0]


_COMPOSE_VAR_PATTERN = re.compile(
    r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:?[-?])?([^}]*)\}"
)


def _substitute_compose_vars(text, defaults=None):
    """Best-effort resolution of docker-compose '${VAR}' interpolation
    (e.g. `image: vaultwarden/server:${TAG:-latest}`), which is extremely
    common in compose files pulled straight from a project's README.

    We normally have no access to the user's real environment/.env, so
    only the forms that carry an explicit default (${VAR:-default} /
    ${VAR-default}) can be resolved — the default is substituted in.

    defaults (optional, 2026-07-20): a dict of real values to try FIRST,
    typically the sibling env-example file fetched alongside a compose
    pulled from a URL (see fetch_env_example_from_url) — the same file a
    real `docker compose` invocation would read its own '.env' from. Using
    it here too means a bare '${DB_PASSWORD}' (no inline default) can
    still resolve correctly when the upstream project already publishes
    that default, instead of being left unresolved.

    Anything still not covered by either (${VAR}, ${VAR:?msg}, ${VAR?msg})
    is left untouched (rule #1: never invent a value) and its name is
    reported back so the caller can warn the user instead of silently
    shipping a broken '${VAR}' string."""
    unresolved = []
    defaults = defaults or {}

    def _replace(match):
        name, operator, rest = match.group(1), match.group(2), match.group(3)
        if name in defaults:
            return defaults[name]
        if operator in (":-", "-"):
            return rest
        unresolved.append(name)
        return match.group(0)

    resolved_text = _COMPOSE_VAR_PATTERN.sub(_replace, text)
    return resolved_text, unresolved


def parse_docker_run_command(text, lang):
    """Parses a `docker run ...` command (the kind typically found on
    Docker Hub/GitHub) and extracts image/port/data/variables from it —
    without going through a docker-compose.yml. Handles commands spread
    over multiple lines with '\\' continuations (the usual tutorial
    format). Philosophy changed on 2026-07-13 at Patrick's request: the
    user gives ONE SINGLE raw input (image, docker run command, or
    docker-compose.yml), never a list of fields to fill in by hand."""
    # Joins lines split by a trailing '\' (shell continuation).
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
    warnings = []
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
            # Multiple -p flags are common (e.g. an HTTP port + a metrics
            # port) but this form only carries one — the first one found
            # is kept (predictable), the rest are reported so nothing is
            # silently dropped without the user knowing.
            if result["container_port"] is None:
                result["container_port"] = _strip_port_protocol(tokens[i + 1].split(":")[-1])
            else:
                warnings.append(t("err_docker_run_duplicate_port", lang))
            i += 2
            continue
        if tok in ("-v", "--volume") and i + 1 < len(tokens):
            parts = tokens[i + 1].split(":")
            if len(parts) >= 2:
                # Either a named volume (source has no leading '/') or a
                # host path mount (e.g. -v /vw-data/:/data/) — either way
                # we want the path INSIDE the container, i.e. the part
                # after the ':'. Same "first wins, rest reported" rule as
                # for -p above.
                if result["data_path"] is None:
                    result["data_path"] = parts[1]
                else:
                    warnings.append(t("err_docker_run_duplicate_volume", lang))
            i += 2
            continue
        if tok in ("-e", "--env") and i + 1 < len(tokens):
            k, _, v = tokens[i + 1].partition("=")
            env_pairs.append((k.strip(), v.strip()))
            i += 2
            continue
        if tok.startswith("-"):
            # Unrecognized option (--name, --restart, -d...): ignored,
            # along with its argument if not glued to it (e.g. --name X).
            # Simple heuristic: if the next token doesn't start with '-'
            # and isn't the image (last token), skip it too.
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-") and i + 1 != len(tokens) - 1:
                i += 2
            else:
                i += 1
            continue
        # What's left is the image (last positional token).
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

    result["warnings"] = warnings
    return result


def smart_parse_input(text, lang, env_example_text=None):
    """Single entry point: automatically detects what the user pasted — a
    'docker run' command, a docker-compose.yml, or just an image name —
    and calls the right parser. "Zero-form" philosophy decided on
    2026-07-13: one single box to fill in, not three different formats to
    choose between yourself.

    env_example_text (optional, 2026-07-20): raw content of a sibling
    env-example file, when the input came from a URL (see
    fetch_env_example_from_url and the /parse_input route) — forwarded to
    parse_compose_snippet to fill in services that declare `env_file:`.

    Also adds a "suggested_mode" key (2026-07-18, see KNOWN_SPA_IMAGES
    above) when the detected image is a known SPA — the add.html page
    uses it to pre-select "dedicated subdomain" mode instead of leaving
    the user to notice and read the generic help text."""
    stripped = text.strip()
    if not stripped:
        raise DockerConnectorError(t("err_nothing_to_analyze", lang))

    if stripped.startswith("docker "):
        result = parse_docker_run_command(stripped, lang)
    # A docker-compose.yml almost always contains at least one line break
    # and a "services:" or "image:" structure. A plain image name, on the
    # other hand, fits on a single line without a ':' followed by a space.
    elif "\n" in stripped or stripped.lstrip().startswith(("services:", "image:")):
        result = parse_compose_snippet(stripped, lang, env_example_text=env_example_text)
    # Otherwise: probably just an image name (e.g. "vaultwarden/server:latest").
    elif re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._/-]*(:[a-zA-Z0-9._-]+)?", stripped):
        result = inspect_docker_image(stripped, lang)
    else:
        raise DockerConnectorError(t("err_unrecognized_format", lang))

    if result.get("multi_service"):
        for service_result in result["services"]:
            if _looks_like_spa(service_result.get("image")):
                service_result["suggested_mode"] = "subdomain"
    elif _looks_like_spa(result.get("image")):
        result["suggested_mode"] = "subdomain"
    result.setdefault("warnings", [])
    return result


def _is_internal_service_reference(url_value, sibling_service_keys):
    """True if a 'http://...' env value's host is actually another
    service's compose key (e.g. IMMICH_MACHINE_LEARNING_URL=http://immich-
    machine-learning:3003 in a multi-service compose) rather than the
    app's own public base URL. Found while testing the Immich compose for
    the multi-container mode (2026-07-20): without this check, such a
    value would be mistaken for the app's own base URL and silently
    overwritten by create_docker_app's auto-computed domain/path — quietly
    breaking the app's connection to its companion."""
    if not sibling_service_keys:
        return False
    try:
        host = url_value.split("://", 1)[1].split("/")[0].split(":")[0]
    except IndexError:
        return False
    return host in sibling_service_keys


def _extract_compose_service_fields(service, service_key, lang, sibling_service_keys=None, env_example_vars=None):
    """Extracts image/port/data/env from a single compose service block —
    the exact same extraction rules regardless of whether the compose file
    declares one service or several (see parse_compose_snippet). Returns
    (result_dict, warnings_list).

    env_example_vars (optional, 2026-07-20): a dict already parsed from a
    sibling '.env.example'-style file fetched from the SAME upstream repo
    as the compose (see fetch_env_example_from_url) — used as the
    service's env_file contents when it declares `env_file:`. Deliberately
    NOT a Docker Gate-maintained catalog (Patrick, 2026-07-20: "zéro
    catalogue à maintenir") — purely mechanical: we only ever read what
    the upstream project already publishes next to its own compose file,
    the same way a human would open both files side by side."""
    result = {"image": None, "container_port": None, "data_path": None, "env_vars": None, "url_env_var": None,
              "service_key": service_key,
              "suggested_slug": service.get("container_name") or service_key}
    warnings = []
    pairs = []

    if service.get("env_file"):
        if env_example_vars:
            pairs.extend(env_example_vars.items())
        else:
            warnings.append(t("err_compose_env_file_not_supported", lang))

    if "image" in service:
        result["image"] = str(service["image"])

    ports = service.get("ports")
    if ports and isinstance(ports, list) and ports:
        first = str(ports[0])
        # Possible formats: "3001", "3001:3001", "127.0.0.1:3001:3001",
        # any of which may also carry a "/udp" or "/tcp" protocol suffix.
        result["container_port"] = _strip_port_protocol(first.split(":")[-1])
        if len(ports) > 1:
            warnings.append(t("err_compose_multiple_ports", lang))

    volumes = service.get("volumes")
    if volumes and isinstance(volumes, list):
        candidates_found = 0
        for v in volumes:
            v_str = str(v)
            parts = v_str.split(":")
            if len(parts) < 2:
                continue
            source = parts[0]
            # Ignore special host mounts (absolute path as the source, e.g.
            # /var/run/docker.sock) — these aren't ordinary data volumes,
            # just taking "the first one found" gave bad results on real
            # files (e.g. Portainer, whose first volume is the Docker
            # socket, not its data).
            if source.startswith("/"):
                continue
            candidates_found += 1
            if result["data_path"] is None:
                result["data_path"] = parts[1]
        if candidates_found > 1:
            warnings.append(t("err_compose_multiple_volumes", lang))

    environment = service.get("environment")
    if environment:
        # The docker-compose format accepts two equivalent syntaxes: a
        # list ["KEY=value", ...] or a dict {KEY: value}. Appended AFTER
        # any env_file-derived pairs above so an inline `environment:`
        # value correctly overrides the same key from env_example_vars —
        # same precedence real `docker compose` applies between env_file
        # and environment.
        if isinstance(environment, list):
            for e in environment:
                k, _, v = str(e).partition("=")
                pairs.append((k.strip(), v.strip()))
        elif isinstance(environment, dict):
            pairs.extend((str(k), str(v)) for k, v in environment.items())

    if pairs:
        merged = dict(pairs)
        # Spot a possible "base URL" variable (a value that looks like a
        # web address, e.g. DOMAIN=https://vw.domain.tld) — this variable
        # doesn't need to be copied as-is: its real value will be computed
        # automatically from the domain and path chosen in the form
        # (simplification requested by Patrick on 2026-07-13, to avoid
        # entering it twice by hand).
        other_lines = []
        for key, value in merged.items():
            if (not result["url_env_var"] and re.match(r"^https?://", value)
                    and not _is_internal_service_reference(value, sibling_service_keys)):
                result["url_env_var"] = key
            else:
                other_lines.append(f"{key}={value}")
        if other_lines:
            result["env_vars"] = "\n".join(other_lines)

    return result, warnings


_SECRET_KEY_RE = re.compile(r"(PASSWORD|PASSWD|SECRET|TOKEN|_KEY)$")


def _autogenerate_secrets(parsed_services):
    """Auto-generates a strong random value for every secret-looking env
    var found across a multi-service compose (key ending in PASSWORD,
    PASSWD, SECRET, TOKEN or _KEY), then propagates each generated value
    to every OTHER service that referenced the exact same original
    literal — this is the concrete friction found testing Immich live
    (2026-07-20): its real compose has the same weak "postgres" password
    typed once in the database service's own block and typed AGAIN by
    hand as DB_PASSWORD wherever it's referenced, with nothing tying the
    two together for the user. Which service ends up "main" vs
    "companion" isn't known yet at parse time (the picker decides that
    afterwards) — so this runs uniformly across every service rather than
    guessing; whatever value lands in the form is always shown, editable,
    never hidden (rule #1), so a genuinely user-facing credential (e.g. an
    admin password on the exposed service) can still be reviewed/replaced
    before install.

    Returns a list of "KEY (service)" labels for the ones actually
    generated, empty if there was nothing secret-looking to replace."""
    replacements = {}
    generated_labels = []
    for service in parsed_services:
        if not service.get("env_vars"):
            continue
        new_lines = []
        for line in service["env_vars"].splitlines():
            key, sep, value = line.partition("=")
            if sep and value and value not in replacements and _SECRET_KEY_RE.search(key.strip().upper()):
                new_value = secrets.token_urlsafe(24)
                replacements[value] = new_value
                generated_labels.append(f"{key.strip()} ({service.get('service_key') or '?'})")
                new_lines.append(f"{key}={new_value}")
            else:
                new_lines.append(line)
        service["env_vars"] = "\n".join(new_lines)

    if not replacements:
        return []

    for service in parsed_services:
        if not service.get("env_vars"):
            continue
        new_lines = []
        for line in service["env_vars"].splitlines():
            key, sep, value = line.partition("=")
            # Destination key must ALSO look secret-like, not just share the
            # same literal value — otherwise an unrelated var that happens
            # to have the same value by coincidence (e.g. a username
            # matching a weak example password like "postgres") would get
            # silently rewritten too. Found by testing before shipping.
            if sep and value in replacements and _SECRET_KEY_RE.search(key.strip().upper()):
                new_lines.append(f"{key}={replacements[value]}")
            else:
                new_lines.append(line)
        service["env_vars"] = "\n".join(new_lines)

    return generated_labels


def parse_compose_snippet(text, lang, env_example_text=None):
    """Extracts image/port/data from a docker-compose.yml snippet pasted by
    the user — many self-hosted projects publish a ready-made one (unlike
    the rest of their docs, often free-text, this format is structured and
    reliable to parse automatically).

    Accepts both a full file (with a `services:` key) and a plain snippet
    of a single service's block. Only fills in what it finds — it's up to
    the user to complete the rest if needed, no invented defaults out of
    thin air (rule #1: never state something that hasn't been verified).

    env_example_text (optional, 2026-07-20): raw content of a sibling
    env-example file fetched from the same upstream repo as the compose
    (see fetch_env_example_from_url) — used to fill in any service that
    declares `env_file:` instead of leaving it as a "add manually"
    warning. Malformed content is ignored silently (best-effort — an
    upstream formatting quirk must never block the analysis of an
    otherwise valid compose).

    When the compose declares MORE THAN ONE service (e.g. an app + its
    database + a cache), every service is extracted and returned as a list
    under "multi_service"/"services" instead of picking just the first one
    silently — the caller (smart_parse_input -> the add.html UI) is
    responsible for letting the user choose which single service is
    exposed via YunoHost/SSO, the others becoming internal companions (see
    create_docker_app's `companions` parameter, semi-piloted multi-container
    mode decided with Patrick on 2026-07-20)."""
    env_example_vars = None
    if env_example_text:
        try:
            env_example_vars = parse_env_vars_text(env_example_text, lang)
        except DockerConnectorError:
            pass

    text, unresolved_vars = _substitute_compose_vars(text, defaults=env_example_vars)

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
    else:
        # Might be a plain snippet (just a service's block, without the
        # enclosing "services:" key) — necessarily a single service.
        services = {None: data}

    compose_warnings = []
    if unresolved_vars:
        compose_warnings.append(t("err_compose_unresolved_vars", lang, vars=", ".join(sorted(set(unresolved_vars)))))

    if len(services) > 1:
        all_service_keys = set(services.keys())
        parsed_services = []
        env_example_applied = False
        for service_key, service in services.items():
            if not isinstance(service, dict):
                raise DockerConnectorError(t("err_unrecognized_service_format", lang))
            sibling_keys = all_service_keys - {service_key}
            if env_example_vars and service.get("env_file"):
                env_example_applied = True
            service_result, service_warnings = _extract_compose_service_fields(
                service, service_key, lang, sibling_keys, env_example_vars=env_example_vars)
            service_result["warnings"] = service_warnings
            parsed_services.append(service_result)
        if not any(s["image"] for s in parsed_services):
            raise DockerConnectorError(t("err_nothing_extracted", lang))
        if env_example_applied:
            compose_warnings.append(t("info_env_example_used", lang))
        generated = _autogenerate_secrets(parsed_services)
        if generated:
            compose_warnings.append(t("info_secrets_autogenerated", lang, list=", ".join(generated)))
        return {"multi_service": True, "services": parsed_services, "warnings": compose_warnings}

    service_key, service = next(iter(services.items()))
    if not isinstance(service, dict):
        raise DockerConnectorError(t("err_unrecognized_service_format", lang))

    result, service_warnings = _extract_compose_service_fields(service, service_key, lang, env_example_vars=env_example_vars)
    if env_example_vars and service.get("env_file"):
        compose_warnings.append(t("info_env_example_used", lang))

    if not result["image"] and not result["container_port"] and not result["data_path"] and not result["env_vars"]:
        raise DockerConnectorError(t("err_nothing_extracted", lang))

    result["warnings"] = compose_warnings + service_warnings
    return result


def parse_env_vars_text(text, lang):
    """Parses a 'KEY=value' text (one per line, like a .env file) into a
    dict. Ignores empty lines and comments (lines starting with #). Raises
    a clear error if a non-empty line doesn't contain an '=' (rule #1:
    never fail silently — better to warn the user than silently ignore a
    malformed line that could matter to the app)."""
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


def build_create_steps(mode):
    """Builds the ordered list of planned step KEYS for a creation,
    depending only on the mode now (2026-07-20 rewrite: creation always
    goes through the same `docker compose` flow — writing the file then
    `up` — regardless of single vs multi-container, so there's no more
    has_data/has_companions branching to keep in sync here). Used both to
    prepare the progress display AND by create_docker_app to report its
    real progress — the two can therefore never fall out of sync.

    Returns stable keys (i18n.STRINGS), never directly displayable text —
    translation happens at display time (progress.html), never here (these
    keys must stay independent of the user's language, including to match
    the progress job, see progress.py)."""
    steps = ["step_check_params", "step_pick_port"]
    if mode == "subdomain":
        steps += [
            "step_create_domain",
            "step_dns_diag",
            "step_web_diag",
            "step_get_cert",
            "step_check_cert",
        ]
    steps += ["step_write_compose", "step_compose_up", "step_expose_app"]
    return steps


def check_subdomain_status(new_subdomain, domain_parent, lang):
    """Checks the state of a potential subdomain BEFORE any creation
    attempt, to give the user clear, non-blocking feedback (Patrick's
    request, 2026-07-13) rather than discovering the problem afterwards
    via a YunoHost error.

    Returns a dict with "status" being:
    - "free": doesn't exist, creation possible
    - "exists_empty": already exists but with no app installed on it — can
      be reused as-is (case of a previous interrupted attempt, e.g. a
      certificate that had failed)
    - "exists_used": already exists WITH an app on it — never reusable,
      suggest an alternative name rather than blocking with no way out
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
        # Caution: if it can't be verified, treat it as occupied rather
        # than risk overwriting something (rule #1).
        apps_on_domain = ["?"]

    if apps_on_domain:
        suggestion = f"{new_subdomain}-2"
        return {"status": "exists_used", "domain": target_domain, "suggestion": suggestion}

    return {"status": "exists_empty", "domain": target_domain}


def check_path_status(domain, path, lang):
    """Checks whether domain+path is already occupied by an existing
    YunoHost app, BEFORE the creation attempt — same preventive logic as
    check_subdomain_status for the "dedicated subdomain" mode (UX parity,
    2026-07-15: the "path" mode had no equivalent check until then, the
    failure only surfaced at the final exposure step)."""
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


def _compose_dir(slug):
    """Directory holding the generated docker-compose.yml for an app —
    same on-disk pattern as DATA_FILE (module-relative data/ dir)."""
    return Path(__file__).parent / "data" / "compose" / slug


def _build_compose_document(slug, main_key, image, container_port, host_port, env_vars, data_path, companions):
    """Builds the compose document (a plain dict, dumped to YAML by the
    caller) for a Docker Gate app — one service or several.

    Security boundary (2026-07-20, replacing the earlier hand-rolled SDK
    orchestration — see create_docker_app's docstring): this is built
    ONLY from already-parsed, already-validated fields (image/port/volume/
    env per service, produced by parse_compose_snippet/smart_parse_input)
    — NEVER from the user's raw pasted text. Keys with real risk on a
    shared host (build, privileged, cap_add, devices, network_mode: host,
    secrets, configs, extends) are never read by the parser in the first
    place, so they can never end up here either, no matter what a pasted
    compose file contains.

    Every app — single container or multi — gets its own network and its
    own container_name/volume name(s), forced to the exact
    'docker-gate-{slug}[-{service_key}]' convention the audit functions
    (find_orphan_*) already expect, regardless of what Compose's own
    default project-based naming would have produced."""
    services = {}
    volumes = {}

    main_service = {
        "image": image,
        "container_name": f"docker-gate-{slug}",
        "restart": "unless-stopped",
        "ports": [f"127.0.0.1:{host_port}:{container_port}/tcp"],
    }
    if env_vars:
        main_service["environment"] = env_vars
    if data_path:
        volume_name = f"docker-gate-{slug}-data"
        volumes[volume_name] = {"name": volume_name}
        main_service["volumes"] = [f"{volume_name}:{data_path}"]
    if companions:
        main_service["depends_on"] = [c["service_key"] for c in companions]
    services[main_key] = main_service

    for c in companions:
        service_key = c["service_key"]
        companion_service = {
            "image": c["image"],
            "container_name": f"docker-gate-{slug}-{service_key}",
            "restart": "unless-stopped",
        }
        if c.get("env_vars"):
            companion_service["environment"] = c["env_vars"]
        if c.get("data_path"):
            volume_name = f"docker-gate-{slug}-{service_key}-data"
            volumes[volume_name] = {"name": volume_name}
            companion_service["volumes"] = [f"{volume_name}:{c['data_path']}"]
        services[service_key] = companion_service

    doc = {"services": services, "networks": {"default": {"name": f"docker-gate-{slug}-net"}}}
    if volumes:
        doc["volumes"] = volumes
    return doc


def _run_docker_compose(project_name, compose_path, args, error_message, lang, timeout=180):
    """Runs `docker compose -p <project> -f <file> <args>`. Mirrors
    _run_sudo's style (readable DockerConnectorError with the real stderr
    on failure) but needs no sudo rule: the app's system user is already a
    member of the `docker` group (see conf/docker_gate.sudoers header +
    `usermod -aG docker` in scripts/install), so the CLI talks to the
    Docker socket exactly like the SDK calls it replaces used to."""
    result = subprocess.run(
        ["docker", "compose", "-p", project_name, "-f", str(compose_path)] + args,
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise DockerConnectorError(
            t("err_sudo_detail", lang, message=error_message, detail=result.stderr.strip() or result.stdout.strip())
        )
    return result.stdout


def _teardown_compose_project(project_name, compose_path):
    """Best-effort `docker compose down -v` after a failed `up` — a SINGLE
    call now handles what used to be 3 separate hand-rolled rollback
    blocks (companions, network, volume). Errors swallowed on purpose:
    runs while another DockerConnectorError is already about to be
    raised/re-raised; the Audit page can find and report any residue this
    leaves behind, same philosophy as the rest of this module."""
    try:
        subprocess.run(
            ["docker", "compose", "-p", project_name, "-f", str(compose_path), "down", "-v"],
            capture_output=True, text=True, timeout=180,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


def create_docker_app(slug, image, container_port, mode, domain, domain_parent, path, new_subdomain, visibility, lang, data_path="", env_vars=None, url_env_var="", reuse_existing_domain=False, companions=None, main_service_key=None, on_step=None):
    """Main entry point for creating an exposed Docker app.

    mode: "path" or "subdomain"
    - path      : exposes at {domain}{path}
    - subdomain : creates {new_subdomain}.{domain_parent}, exposes at the root

    domain_parent is a DISTINCT field from domain (two separate dropdowns
    in the form, one per mode) — never mix them up, an incident already
    encountered and fixed on 2026-07-12.

    lang: the language of the user who launched the creation, captured
    from the original HTTP request (see app.py) — creation runs in a
    separate thread, with no direct access to Flask/session context, hence
    this explicit parameter rather than an implicit inference (2026-07-15,
    i18n).

    data_path (optional): path INSIDE the container where the app stores
    its persistent data (e.g. "/app/data" for Uptime Kuma — see the app's
    documentation on Docker Hub). If provided, a dedicated named Docker
    volume is created and mounted there, so the data survives a container
    restart or recreation.

    on_step (optional): function called with the KEY of each step as it
    starts (see build_create_steps and progress.py) — lets the interface
    show detailed progress during long operations (image download, Let's
    Encrypt certificate).

    env_vars (optional): dict of environment variables to pass to the
    container.

    url_env_var (optional): name of an environment variable to
    AUTOMATICALLY compute and inject with the app's full address once
    known (e.g. "DOMAIN", "ROOT_URL" — the exact name depends on the app,
    see its documentation). Avoids having to type a URL yourself that must
    stay in sync with the domain/path chosen elsewhere — simplification
    requested by Patrick on 2026-07-13, after a first attempt deemed too
    manual/error-prone.

    reuse_existing_domain (optional, subdomain mode only): if True, does
    NOT try to create the YunoHost domain (it already exists and was
    verified empty via check_subdomain_status) — avoids a YunoHost error on
    an already-declared domain. Also serves as a natural resume mechanism:
    if the certificate fails on a first attempt, the domain stays created;
    relaunching the install with this parameter just picks up right after,
    without starting over.

    companions (optional, semi-piloted multi-container mode, 2026-07-20):
    list of dicts {service_key, image, data_path, env_vars} for the OTHER
    services of a multi-service docker-compose.yml (e.g. a database, a
    cache) that must run alongside the main container on a dedicated
    Docker network, without any YunoHost/SSO exposure or published port.
    main_service_key is the original compose key of the exposed service
    itself (defaults to "app" when the input wasn't a multi-service
    compose, e.g. a plain image or a `docker run` command).

    Implementation (rewritten 2026-07-20, following Patrick's review — see
    docs/CARNET-DE-BORD.md): rather than hand-rolling network creation,
    per-container network aliasing and a bespoke rollback tree via the
    Docker SDK, this generates a minimal docker-compose.yml (see
    _build_compose_document) and drives it entirely through the real
    `docker compose` CLI (see _run_docker_compose). Compose already gives
    every service DNS resolution by its own service key on the project's
    network for free — no manual aliasing code needed — and a single
    `docker compose down -v` cleanly undoes a failed `up`, replacing 3
    separate rollback blocks. Every container/volume/network name is
    forced to the exact 'docker-gate-{slug}[-{service_key}]' convention
    the audit functions already expect, so env vars copied verbatim from
    the source compose (e.g. DATABASE_URL=postgres://user:pass@db/db)
    keep resolving correctly with zero rewriting — "db" is both the
    compose service key and its own DNS name on the network.

    Raises DockerConnectorError with a clear message at every step that can
    genuinely fail in a blocking way (invalid parameters, unavailable port,
    Docker refusing to start the container...), so the user understands
    what got stuck (rule #1: never fail silently).

    Decision from 2026-07-14 (Patrick, following issue #49): in "subdomain"
    mode, DNS not yet propagated at the registrar must NO LONGER block the
    whole installation (failed DNS/Web diagnosis, unobtainable Let's
    Encrypt certificate) — the app is still exposed with whatever
    certificate is available (even self-signed), and a warning is recorded
    in `entry["warnings"]` instead of cancelling everything. Point checked
    (rule #1, 2026-07-14): YunoHost's daily cron (`yunohost domain cert
    renew`) only renews an existing Let's Encrypt certificate close to
    expiring — it NEVER switches a domain still on a self-signed
    certificate over to Let's Encrypt on its own. Once DNS has propagated,
    the install must therefore be relaunched (the existing subdomain will
    be detected and reused via `reuse_existing_domain`), not just waited
    out.
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

    # --- Resolving the target domain/path depending on the mode ---
    if mode == "subdomain":
        if not new_subdomain or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", new_subdomain):
            raise DockerConnectorError(t("err_invalid_subdomain", lang))
        target_domain = f"{new_subdomain}.{domain_parent}"
        target_path = "/"

        if reuse_existing_domain:
            # The subdomain already exists and was verified empty (see
            # check_subdomain_status) — it isn't recreated, YunoHost would
            # refuse an already-declared domain anyway.
            pass
        else:
            step("step_create_domain")
            _run_sudo(
                ["yunohost", "domain", "add", target_domain],
                t("err_create_subdomain", lang, domain=target_domain),
                lang,
            )

        # A diagnosis must exist before a certificate can be requested
        # (lesson learned on 2026-07-10, Portainer incident). Their results
        # are checked, but since 2026-07-14 a failure here no longer
        # cancels the installation (Patrick's decision, issue #49): it's
        # the most common sign of a DNS zone not yet configured at the
        # registrar — we warn instead of blocking, the app will be exposed
        # anyway with whatever certificate is available (see below).
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
        # `yunohost domain cert install` fails with a non-zero code if a
        # valid certificate already exists on this domain (the normal case
        # for the "reuse this existing subdomain" mode) — this isn't a
        # real error in itself, so its return code is deliberately not
        # used here to decide whether to warn (see below, found on
        # 2026-07-18: the reuse case was triggering a false "certificate
        # not obtained" warning even though the existing certificate
        # remained valid throughout).
        subprocess.run(
            ["/usr/bin/sudo", "-n", "yunohost", "domain", "cert", "install", target_domain],
            capture_output=True, text=True, timeout=180,
        )

        # Only the real check of the certificate's status is authoritative,
        # never just the return code of the install command above: `cert
        # install` can return 0 without having actually installed a Let's
        # Encrypt certificate (YunoHost bug: silently continues when the
        # domain isn't ready for ACME yet — discovered on 2026-07-13 on
        # test1.wappos.fr, no DNS at OVH), AND can return a non-zero code
        # even though everything is fine (case of reusing a domain that
        # already has a valid certificate, found on 2026-07-18 on
        # portainer.wappos.fr).
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

        # ca_type is None only when the check itself failed (exception
        # above, warning already added at that point) — don't duplicate a
        # second warning for the same failure.
        if ca_type and ca_type != "letsencrypt":
            # Split into 4 separate bullets (2026-07-18, Patrick's feedback)
            # instead of one dense paragraph — each check gets its own line
            # in the install summary so none of them gets skipped over.
            warnings.append(t("warn_cert_not_letsencrypt", lang, domain=target_domain, ca_type=ca_type))
            warnings.append(t("warn_cert_check_dns", lang, domain=target_domain))
            warnings.append(t("warn_cert_check_passthrough", lang, domain=target_domain))
            warnings.append(t("warn_cert_retry_tip", lang))
    else:
        target_domain = domain
        target_path = path if path.startswith("/") else f"/{path}"

    # --- Automatically computed base URL variable (optional) ---
    # The path ("/") must not be doubled at the end of the URL (e.g. avoid
    # "https://x.fr/vaultwarden-test/" in subdomain mode where target_path
    # is already "/").
    if url_env_var:
        env_vars = dict(env_vars) if env_vars else {}
        if target_path == "/":
            env_vars[url_env_var] = f"https://{target_domain}/"
        else:
            env_vars[url_env_var] = f"https://{target_domain}{target_path}"

    # --- Compose project: one docker-compose.yml per app, driven by the
    # real `docker compose` CLI (see this function's docstring,
    # _build_compose_document and _run_docker_compose) ---
    main_key = main_service_key or "app"
    project_name = f"docker-gate-{slug}"
    compose_path = _compose_dir(slug) / "docker-compose.yml"

    step("step_write_compose")
    compose_doc = _build_compose_document(
        slug=slug, main_key=main_key, image=image, container_port=container_port,
        host_port=host_port, env_vars=env_vars, data_path=data_path, companions=companions or [],
    )
    try:
        compose_path.parent.mkdir(parents=True, exist_ok=True)
        with open(compose_path, "w") as f:
            yaml.safe_dump(compose_doc, f, sort_keys=False)
    except OSError as e:
        raise DockerConnectorError(t("err_write_compose", lang, error=e))

    step("step_compose_up")
    _run_docker_compose(
        project_name, compose_path, ["config", "-q"],
        t("err_compose_config_invalid", lang), lang, timeout=30,
    )
    try:
        _run_docker_compose(
            project_name, compose_path,
            ["up", "-d", "--wait", "--wait-timeout", "120", "--pull", "missing"],
            t("err_compose_up_failed", lang), lang, timeout=240,
        )
    except DockerConnectorError:
        # A single `down -v` undoes whatever `up` managed to start before
        # failing — no per-resource rollback bookkeeping needed anymore.
        _teardown_compose_project(project_name, compose_path)
        raise

    container_name = f"docker-gate-{slug}"
    volume_name = f"docker-gate-{slug}-data" if data_path else None
    network_name = f"docker-gate-{slug}-net"
    companion_entries = [
        {
            "service_key": c["service_key"],
            "container_name": f"docker-gate-{slug}-{c['service_key']}",
            "image": c["image"],
            "volume_name": f"docker-gate-{slug}-{c['service_key']}-data" if c.get("data_path") else None,
            "data_path": c.get("data_path"),
            "env_var_keys": sorted(c["env_vars"].keys()) if c.get("env_vars") else [],
        }
        for c in (companions or [])
    ]

    # --- Exposure via the official "redirect" app ---
    step("step_expose_app")
    # Direct passthrough of YunoHost's native vocabulary (admins/all_users/
    # visitors) — audit 2026-07-17, docs/02-wappos/audits/2026-07-17-audit-permissions-yunohost.md.
    # Falls back to the most restrictive if an unexpected value ever
    # arrived here (defense in depth, the main validation is already done
    # in app.py).
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
        # Don't leave a running-but-unexposed app behind if exposure fails.
        _teardown_compose_project(project_name, compose_path)
        raise

    apps_after = {a["id"] for a in json.loads(
        _run_sudo(["yunohost", "app", "list", "--output-as", "json"], t("err_list_apps", lang), lang)
    )["apps"]}
    new_app_ids = apps_after - apps_before
    yunohost_app_id = next(iter(new_app_ids), None)

    # --- Docker Gate logo on the exposed "redirect" instance (best-effort:
    # a missing icon must never fail a creation that otherwise succeeded) ---
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
        "network_name": network_name,
        "companions": companion_entries,
        "compose_project": project_name,
        "compose_file": str(compose_path),
    }
    apps = _load_state()
    apps.append(entry)
    _save_state(apps)
    entry["warnings"] = warnings
    return entry


def remove_docker_app(slug, lang, delete_data=False, delete_domain=False):
    """Removes an app in 3 distinct layers, checked separately (rule #30 —
    multi-level verification, lesson from 2026-07-10):
    1) SSO permission + nginx config (via `yunohost app remove`)
    2) Docker container
    3) entry in our state file

    delete_data (default False): see create_docker_app — never deleted by
    default, an explicit checkbox is required.

    delete_domain (default False, only relevant in "subdomain" mode): if
    checked, also removes the dedicated YunoHost domain created for this
    app. A watch point specific to a multi-VM architecture with
    TLS-passthrough (like BYRTN's): this does NOT clean up the passthrough
    entry on the relay VM, if any (out of this app's reach) — remove it by
    hand if needed.

    Each step is attempted independently (best-effort): a failure at one
    step never prevents the next ones from running, and the entry is
    always removed from the state file at the end — a partial failure must
    never leave Docker Gate in an inconsistent state where it "believes" an
    app still exists when it has been partially dismantled (hardened on
    2026-07-15, following a robustness audit: before this fix, an
    unexpected failure at an intermediate step could interrupt the whole
    removal without ever updating the state). Failures are surfaced as
    warnings (see the returned entry["warnings"]) rather than blocking,
    consistent with the handling already in place for creation (see
    create_docker_app).
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

    if entry.get("compose_project"):
        # Compose-based app (2026-07-20 rewrite): one call tears down the
        # container(s), the dedicated network, and — with -v — the
        # volume(s), all at once. Falls back to `-p <project>` alone
        # (no -f) if the compose file went missing (e.g. manual tampering,
        # data/ wiped by hand) — Compose can still find its own resources
        # by their project label, same "never fail silently, always try
        # the next best thing" spirit as the rest of this module.
        compose_file = Path(entry["compose_file"]) if entry.get("compose_file") else None
        down_args = ["down", "-v"] if delete_data else ["down"]
        try:
            if compose_file and compose_file.exists():
                _run_docker_compose(entry["compose_project"], compose_file, down_args, t("err_compose_down_failed", lang), lang)
            else:
                result = subprocess.run(
                    ["docker", "compose", "-p", entry["compose_project"]] + down_args,
                    capture_output=True, text=True, timeout=180,
                )
                if result.returncode != 0:
                    raise DockerConnectorError(t("err_sudo_detail", lang, message=t("err_compose_down_failed", lang), detail=result.stderr.strip()))
        except DockerConnectorError as e:
            warnings.append(str(e))
        if compose_file and compose_file.parent.exists():
            try:
                shutil.rmtree(compose_file.parent)
            except OSError:
                pass
    else:
        # Legacy path (apps created before this rewrite, e.g. pre-existing
        # portainer/dashy on wappos-lab): same hand-rolled SDK removal as
        # before, kept unchanged — no forced migration.
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

        for companion in entry.get("companions", []):
            try:
                container = docker_client.containers.get(companion["container_name"])
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass
            except docker.errors.APIError as e:
                warnings.append(t("err_remove_companion_container", lang, name=companion["container_name"], error=e))

            if delete_data and companion.get("volume_name"):
                try:
                    docker_client.volumes.get(companion["volume_name"]).remove()
                except docker.errors.NotFound:
                    pass
                except docker.errors.APIError as e:
                    warnings.append(t("err_remove_companion_volume", lang, name=companion["volume_name"], error=e))

        if entry.get("network_name"):
            try:
                docker_client.networks.get(entry["network_name"]).remove()
            except docker.errors.NotFound:
                pass
            except docker.errors.APIError as e:
                warnings.append(t("err_remove_network", lang, name=entry["network_name"], error=e))

    if delete_domain and entry.get("mode") == "subdomain":
        try:
            _run_sudo(
                ["yunohost", "domain", "remove", entry["domain"]],
                t("err_remove_domain", lang, domain=entry["domain"]),
                lang,
            )
        except DockerConnectorError as e:
            warnings.append(str(e))

    # Always remove the entry from the state file, even after a partial
    # failure above — real residue (an un-removed container/volume/domain)
    # stays detectable and actionable from the Audit & cleanup page, rather
    # than blocking removal indefinitely.
    apps = [a for a in apps if a["slug"] != slug]
    _save_state(apps)

    return warnings


# =================================================
# RESIDUE AUDIT (step 3, 2026-07-12)
# =================================================
# Principle: Docker Gate must be able to find on its own whatever it left
# behind (partial failures, forgotten tests) rather than relying on the
# user to think of it every time. Each category carries a different risk
# level: orphan containers and unused images are safe to clean up (no real
# configuration/data loss), orphan volumes may contain real data (a
# cautious action, one at a time, never bulk), empty domains are never
# removed automatically (only reported — a domain might be useful in a way
# this app has no knowledge of).

def _known_container_names():
    """Every Docker container name Docker Gate currently tracks — the main
    container of each app plus its companions, if any (semi-piloted
    multi-container mode, 2026-07-20) — used to tell a real orphan apart
    from a container that's simply part of a multi-container app."""
    apps = _load_state()
    names = {a["container_name"] for a in apps}
    names |= {c["container_name"] for a in apps for c in a.get("companions", [])}
    return names


def _known_volume_names():
    """Same idea as _known_container_names, for volumes (main app +
    companions)."""
    apps = _load_state()
    names = {a["volume_name"] for a in apps if a.get("volume_name")}
    names |= {c["volume_name"] for a in apps for c in a.get("companions", []) if c.get("volume_name")}
    return names


def _known_network_names():
    """Every Docker network name Docker Gate currently tracks (one per
    multi-container app, see create_docker_app)."""
    return {a["network_name"] for a in _load_state() if a.get("network_name")}


def find_orphan_containers():
    """Docker containers named 'docker-gate-*' but absent from our state
    file — leftovers from an interrupted creation/removal."""
    known_names = _known_container_names()
    orphans = []
    for c in docker_client.containers.list(all=True):
        if c.name.startswith("docker-gate-") and c.name not in known_names:
            orphans.append({"name": c.name, "status": c.status, "image": c.image.tags})
    return orphans


def find_orphan_volumes():
    """Docker volumes named 'docker-gate-*-data' but absent from our state
    file — never bulk-deleted, one at a time and with explicit confirmation
    (may contain real data)."""
    known_volumes = _known_volume_names()
    orphans = []
    for v in docker_client.volumes.list():
        if v.name.startswith("docker-gate-") and v.name.endswith("-data") and v.name not in known_volumes:
            orphans.append({"name": v.name})
    return orphans


def find_orphan_networks():
    """Docker networks named 'docker-gate-*-net' but absent from our state
    file — same leftover scenario as orphan containers/volumes, for the
    per-app network created in multi-container mode."""
    known_networks = _known_network_names()
    orphans = []
    for n in docker_client.networks.list():
        if n.name.startswith("docker-gate-") and n.name.endswith("-net") and n.name not in known_networks:
            orphans.append({"name": n.name})
    return orphans


def find_dangling_images():
    """'Dangling' Docker images (unnamed, with no container using them) —
    a standard and safe kind of Docker residue, unrelated to our own apps."""
    images = docker_client.images.list(filters={"dangling": True})
    return [{"id": img.short_id, "size_mb": round(img.attrs.get("Size", 0) / (1024 * 1024), 1)} for img in images]


def remove_orphan_container(name, lang):
    """Removes one specific orphan container (never in bulk)."""
    if name in _known_container_names() or not name.startswith("docker-gate-"):
        raise DockerConnectorError(t("err_container_not_orphan", lang))
    try:
        c = docker_client.containers.get(name)
        c.stop()
        c.remove()
    except docker.errors.NotFound:
        pass


def remove_orphan_volume(name, lang):
    """Removes one specific orphan volume (never in bulk)."""
    if name in _known_volume_names() or not (name.startswith("docker-gate-") and name.endswith("-data")):
        raise DockerConnectorError(t("err_volume_not_orphan", lang))
    try:
        docker_client.volumes.get(name).remove()
    except docker.errors.NotFound:
        pass


def remove_orphan_network(name, lang):
    """Removes one specific orphan network (never in bulk)."""
    if name in _known_network_names() or not (name.startswith("docker-gate-") and name.endswith("-net")):
        raise DockerConnectorError(t("err_network_not_orphan", lang))
    try:
        docker_client.networks.get(name).remove()
    except docker.errors.NotFound:
        pass


def prune_dangling_images():
    """Cleans up all dangling images — a standard, safe Docker operation
    (equivalent to `docker image prune -f`), no image used by an existing
    container is ever affected."""
    result = docker_client.images.prune(filters={"dangling": True})
    return result.get("SpaceReclaimed", 0)


def find_empty_domains(lang):
    """YunoHost domains with no app installed on them — reported only,
    NEVER removed automatically (a domain might be useful in a way this app
    has no knowledge of)."""
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


# =================================================
# FULL DOCKER CE UNINSTALL (2026-07-18)
# =================================================
# Symmetric to ynh_docker_gate__ensure_docker_installed (scripts/_common.sh),
# which installs Docker CE automatically. Exposed here, in addition to the
# question asked by scripts/remove, because the latter can never appear
# when Docker Gate is removed via the YunoHost admin panel (no terminal
# attached in that case, see the 2026-07-18 journal) — this web page, on
# the other hand, works regardless of how Docker Gate itself was removed.

def docker_ce_status():
    """Current state of Docker CE on the machine: installed or not,
    containers still managed by Docker Gate (which this button would also
    stop — not just "foreign" containers), and containers that are NOT
    managed by Docker Gate. Purging Docker CE destroys both categories
    without distinction: a warning limited to only foreign containers would
    have given a false sense of safety as long as no third-party app was
    present, while apps managed by Docker Gate itself (e.g. Portainer)
    would stop working just the same (point raised by Patrick on
    2026-07-18 after a real test)."""
    installed = shutil.which("docker") is not None
    tracked = []
    foreign = []
    if installed:
        known_names = {a["container_name"] for a in _load_state()}
        try:
            for c in docker_client.containers.list(all=True):
                if c.name in known_names:
                    tracked.append(c.name)
                else:
                    foreign.append(c.name)
        except docker.errors.DockerException:
            # Docker installed but the daemon is unreachable (unlikely, but
            # must never crash the Audit page) — shows the "installed"
            # state without being able to list containers in that case.
            pass
    return {"installed": installed, "tracked_containers": tracked, "foreign_containers": foreign}


def uninstall_docker_ce(lang):
    """Full purge of Docker CE (packages, /var/lib/docker, the system
    docker group) — same logic as the interactive question in
    scripts/remove, exposed here as a web action to cover the case where
    Docker Gate is uninstalled from the admin panel (no terminal attached,
    so the scripts/remove question can never appear then). No additional
    safety check here on foreign containers: the warning is shown on the
    interface side (see docker_ce_status) before the admin clicks,
    consistent with the two-click arming already in place for destructive
    removals on this page."""
    commands = [
        (["systemctl", "stop", "docker", "docker.socket", "containerd"], t("err_docker_ce_stop", lang)),
        (
            [
                "apt-get", "purge", "-y",
                "docker-ce", "docker-ce-cli", "docker-ce-rootless-extras",
                "docker-buildx-plugin", "docker-compose-plugin", "containerd.io",
            ],
            t("err_docker_ce_purge", lang),
        ),
        (["apt-get", "autoremove", "-y"], t("err_docker_ce_autoremove", lang)),
        (["rm", "-rf", "/var/lib/docker", "/var/lib/containerd", "/etc/docker"], t("err_docker_ce_rm", lang)),
        (
            ["rm", "-f", "/etc/apt/sources.list.d/docker.list", "/etc/apt/keyrings/docker.gpg"],
            t("err_docker_ce_rm", lang),
        ),
    ]
    warnings = []
    for args, error_message in commands:
        try:
            _run_sudo(args, error_message, lang)
        except DockerConnectorError as e:
            warnings.append(str(e))

    # groupdel fails if the group no longer exists (e.g. a second attempt)
    # — non-blocking, not a real failure in this specific case.
    try:
        _run_sudo(["groupdel", "docker"], t("err_docker_ce_groupdel", lang), lang)
    except DockerConnectorError:
        pass

    return warnings
