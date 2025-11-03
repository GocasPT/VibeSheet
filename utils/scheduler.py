"""
Background Scheduler - Executa sync periódico com monitoring.
"""
import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from dotenv import load_dotenv
from services.sync_service import SpotifySyncService

load_dotenv()
logger = logging.getLogger(__name__)

# Configuração
SYNC_INTERVAL_SEC = int(os.getenv("SYNC_INTERVAL_SEC", 30))

# Scheduler singleton
_scheduler = BackgroundScheduler(
    job_defaults={
        'coalesce': True,        # Merge jobs atrasados
        'max_instances': 1,      # Previne overlap
        'misfire_grace_time': 10 # Tolera 10s de atraso
    }
)

# Métricas do scheduler
_metrics = {
    "total_runs": 0,
    "successful_runs": 0,
    "failed_runs": 0,
    "last_run_time": None,
    "last_run_status": None,
    "last_error": None
}


def _on_job_event(event):
    """
    Listener para eventos do scheduler.
    Atualiza métricas e logs.
    """
    _metrics["total_runs"] += 1
    _metrics["last_run_time"] = datetime.now().isoformat()
    
    if event.exception:
        _metrics["failed_runs"] += 1
        _metrics["last_run_status"] = "failed"
        _metrics["last_error"] = str(event.exception)
        logger.error(f"Sync job failed: {event.exception}")
    else:
        _metrics["successful_runs"] += 1
        _metrics["last_run_status"] = "success"
        logger.info("Sync job executed successfully")


def _sync_job_wrapper():
    """
    Wrapper com error handling robusto.
    Previne que exceções matem o scheduler.
    """
    try:
        logger.debug("Executando sync periódico...")
        metrics = SpotifySyncService.sync_all_users()
        logger.info(f"Sync periódico concluído: {metrics}")
    
    except Exception as e:
        logger.error(f"Sync job crashed: {e}", exc_info=True)
        # Não propaga exceção para manter scheduler rodando


def start_scheduler():
    """
    Inicia scheduler de sync periódico.
    Thread-safe (pode ser chamado múltiplas vezes).
    """
    if _scheduler.running:
        logger.warning("Scheduler já está rodando")
        return
    
    # Adiciona listener de eventos
    _scheduler.add_listener(_on_job_event, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
    
    # Adiciona job de sync
    _scheduler.add_job(
        _sync_job_wrapper,
        trigger=IntervalTrigger(seconds=SYNC_INTERVAL_SEC),
        id="spotify_sync_job",
        name="Spotify → Sheets Sync",
        replace_existing=True
    )
    
    # Inicia scheduler
    _scheduler.start()
    logger.info(f"⏰ Scheduler iniciado — sync a cada {SYNC_INTERVAL_SEC}s")


def stop_scheduler():
    """
    Para scheduler gracefully.
    Aguarda job atual finalizar.
    """
    if not _scheduler.running:
        logger.warning("Scheduler já está parado")
        return
    
    _scheduler.shutdown(wait=True)
    logger.info("Scheduler parado")


def get_scheduler_status() -> dict:
    """
    Retorna status e métricas do scheduler.
    Útil para endpoint /health.
    """
    jobs = []
    if _scheduler.running:
        for job in _scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            })
    
    return {
        "running": _scheduler.running,
        "interval_sec": SYNC_INTERVAL_SEC,
        "jobs": jobs,
        "metrics": _metrics.copy()
    }


def trigger_manual_sync():
    """
    Dispara sync manual imediatamente (bypassa scheduler).
    Útil para testes e debug.
    """
    logger.info("Sync manual disparado")
    return SpotifySyncService.sync_all_users()