"""APScheduler setup for periodic data collection and analysis."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance."""
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    # TODO: Add scheduled jobs
    # scheduler.add_job(daily_price_update, 'cron', hour=18, minute=0, day_of_week='mon-fri')
    # scheduler.add_job(daily_news_scan, 'cron', hour='8,14', minute=0, day_of_week='mon-fri')
    # scheduler.add_job(weekly_full_analysis, 'cron', day_of_week='sat', hour=9, minute=0)

    return scheduler
