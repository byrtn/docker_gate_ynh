"""
Docker Gate — suivi de progression des opérations longues.

Étape 3 (13/07/2026) : suivi détaillé étape par étape pour les opérations qui
peuvent prendre de quelques secondes à plusieurs minutes (téléchargement
d'image Docker, obtention d'un certificat Let's Encrypt...) — auparavant
aucun retour visuel n'existait pendant ce temps.

Fonctionne en mémoire, dans un seul processus. C'est précisément pour ça que
le service systemd de cette app tourne avec un seul worker gunicorn (voir
conf/systemd.service) : un état gardé en mémoire Python ne serait pas visible
entre plusieurs processus séparés.
"""
import threading
import time
import uuid

_jobs = {}
_lock = threading.Lock()

# Un job terminé n'a plus besoin d'être gardé au-delà du temps qu'il faudrait
# à un admin pour recharger la page de progression après coup. Purgé à
# chaque nouvelle création plutôt que via un thread dédié — largement
# suffisant vu la fréquence d'usage de cet outil (durci le 15/07/2026 :
# sans ça, chaque app créée/supprimée laissait un job en mémoire pour
# toujours, jusqu'au prochain redémarrage du service).
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
    """Crée un nouveau job de suivi, avec la liste ordonnée des étapes prévues
    (des libellés lisibles, ex: "Lancement du conteneur Docker"). Retourne un
    identifiant unique à utiliser pour suivre et faire avancer ce job."""
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
    """Marque l'étape correspondant à `step_label` comme en cours/atteinte.
    On avance par libellé (pas par numéro) pour qu'il n'y ait jamais de
    désynchronisation possible entre la liste déclarée et les appels réels."""
    with _lock:
        if job_id in _jobs:
            job = _jobs[job_id]
            if step_label in job["steps"]:
                job["current"] = job["steps"].index(step_label)


def finish(job_id, warnings=None):
    """Marque le job comme terminé avec succès.

    warnings (optionnel) : points de vigilance non-bloquants remontés
    pendant l'installation (ex: DNS pas encore propagé chez le registrar,
    voir ynh_manager.create_docker_app) — affichés dans le résumé de fin
    d'installation côté interface, sans avoir empêché l'app d'être créée
    (décision du 14/07/2026, anomalie #49)."""
    with _lock:
        if job_id in _jobs:
            job = _jobs[job_id]
            job["done"] = True
            job["current"] = len(job["steps"])
            job["warnings"] = warnings or []


def fail(job_id, error_message):
    """Marque le job comme terminé en échec, avec un message lisible."""
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["done"] = True
            _jobs[job_id]["error"] = error_message


def get_job(job_id):
    """Retourne l'état actuel du job, ou None s'il n'existe pas (ex: après
    un redémarrage du service, la mémoire est vidée — cas géré côté Flask)."""
    with _lock:
        return _jobs.get(job_id)
