"""
Docker Gate — progress tracking for long-running operations.

Step 3 (2026-07-13): detailed step-by-step tracking for operations that can
take anywhere from a few seconds to several minutes (pulling a Docker image,
obtaining a Let's Encrypt certificate...) — previously there was no visual
feedback at all during that time.

Runs in memory, in a single process. That's precisely why this app's systemd
service runs with a single gunicorn worker (see conf/systemd.service): state
kept in Python memory wouldn't be visible across multiple separate processes.
"""
import threading
import time
import uuid

_jobs = {}
_lock = threading.Lock()

# A finished job doesn't need to be kept around longer than it would take an
# admin to reload the progress page afterwards. Pruned on every new job
# creation rather than via a dedicated thread — plenty sufficient given how
# often this tool is used (hardened on 2026-07-15: without this, every app
# created/removed left a job in memory forever, until the next service
# restart).
_JOB_TTL_SECONDS = 3600


def _prune_old_jobs():
    now = time.time()
    expired = [
        jid for jid, job in _jobs.items()
        if job["done"] and now - job["created_at"] > _JOB_TTL_SECONDS
    ]
    for jid in expired:
        del _jobs[jid]


def create_job(steps):
    """Creates a new tracking job, with the ordered list of planned steps
    (human-readable labels, e.g. "Starting the Docker container"). Returns a
    unique identifier used to track and advance this job."""
    job_id = uuid.uuid4().hex
    with _lock:
        _prune_old_jobs()
        _jobs[job_id] = {
            "steps": steps,
            "current": 0,
            "done": False,
            "error": None,
            "warnings": [],
            "created_at": time.time(),
        }
    return job_id


def advance(job_id, step_label):
    """Marks the step matching `step_label` as reached/in progress.
    We advance by label (not by index) so there's never a possible
    desync between the declared list and the actual calls."""
    with _lock:
        if job_id in _jobs:
            job = _jobs[job_id]
            if step_label in job["steps"]:
                job["current"] = job["steps"].index(step_label)


def finish(job_id, warnings=None):
    """Marks the job as successfully finished.

    warnings (optional): non-blocking points to watch, surfaced during
    installation (e.g. DNS not yet propagated at the registrar, see
    ynh_manager.create_docker_app) — shown in the end-of-install summary
    on the interface, without having prevented the app from being created
    (decision from 2026-07-14, issue #49)."""
    with _lock:
        if job_id in _jobs:
            job = _jobs[job_id]
            job["done"] = True
            job["current"] = len(job["steps"])
            job["warnings"] = warnings or []


def fail(job_id, error_message):
    """Marks the job as finished with a failure, with a readable message."""
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["done"] = True
            _jobs[job_id]["error"] = error_message


def get_job(job_id):
    """Returns the job's current state, or None if it doesn't exist (e.g.
    after a service restart, memory is wiped — handled on the Flask side)."""
    with _lock:
        return _jobs.get(job_id)
