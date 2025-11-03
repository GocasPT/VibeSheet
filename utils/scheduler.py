import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from dotenv import load_dotenv

from services.spotify_sync import sync_spotify_to_sheets

load_dotenv()

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()

# Métricas simples
_metrics = {
    "total_runs": 0,
    "successful_runs": 0,
    "failed_runs": 0,
    "last_run": None,
    "last_error": None
}


def _job_listener(event):
    """Monitora execução de jobs para métricas e debug"""
    if event.exception:
        _metrics["failed_runs"] += 1
        _metrics["last_error"] = str(event.exception)
        logger.error(f"Scheduler job failed: {event.exception}")
    else:
        _metrics["successful_runs"] += 1
        _metrics["last_run"] = event.scheduled_run_time
        logger.info("Scheduler job executed successfully")
    
    _metrics["total_runs"] += 1


def _safe_sync():
    """Wrapper com error handling para evitar crashes do scheduler"""
    try:
        sync_spotify_to_sheets()
    except Exception as e:
        logger.error(f"Sync failed in scheduler: {e}", exc_info=True)
        # Não propaga exceção para não matar o scheduler


def start_scheduler():
    """Inicia scheduler com error handling e logging"""
    interval = int(os.getenv("SYNC_INTERVAL_SEC", 30))
    
    scheduler.add_listener(_job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
    
    scheduler.add_job(
        _safe_sync,
        trigger=IntervalTrigger(seconds=interval),
        id="spotify_sync_job",
        replace_existing=True,
        max_instances=1,  # Previne overlap de jobs
        coalesce=True,    # Merge jobs atrasados
        misfire_grace_time=10  # Tolera 10s de atraso
    )
    
    scheduler.start()
    logger.info(f"⏰ Scheduler started — syncing every {interval}s")


def stop_scheduler():
    """Para scheduler gracefully"""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")


def get_scheduler_status() -> dict:
    """Retorna status e métricas do scheduler"""
    return {
        "running": scheduler.running,
        "metrics": _metrics.copy()
    }