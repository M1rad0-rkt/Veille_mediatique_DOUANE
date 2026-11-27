"""Processus d'arrière-plan : collecte périodique + traitement IA. Lancé par le service « worker » de Docker."""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.tasks import jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

if __name__ == "__main__":
    jobs.startup()
    sched = BlockingScheduler(timezone="UTC", job_defaults={"max_instances": 1, "coalesce": True})
    # Chaque source a son propre intervalle (sources.interval_minutes) : on vérifie toutes les minutes ce qui est dû.
    sched.add_job(jobs.collect_due, "interval", seconds=60, id="collect_due")
    sched.add_job(jobs.handle_requests, "interval", seconds=5, id="requests")
    sched.add_job(jobs.process_ai, "interval", seconds=30, id="ai")
    sched.add_job(jobs.heartbeat, "interval", seconds=30, id="heartbeat")
    jobs.heartbeat()
    sched.add_job(jobs.collect_due, id="collect_now")   # première passe immédiate au démarrage
    logging.getLogger(__name__).info("Worker démarré")
    sched.start()
