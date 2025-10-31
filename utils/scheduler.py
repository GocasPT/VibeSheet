import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

from sheets.spotify_sync import sync_spotify_to_sheets

load_dotenv()

scheduler = BackgroundScheduler()


def start_scheduler():
    interval = int(os.getenv("SYNC_INTERVAL_SEC", 30))
    scheduler.add_job(
        sync_spotify_to_sheets,
        trigger=IntervalTrigger(seconds=interval),
        id="spotify_sync_job",
        replace_existing=True,
    )
    scheduler.start()
    print(f"⏰ Scheduler started — syncing every {interval} sec.")
