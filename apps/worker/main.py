"""Worker main application with APScheduler."""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from apps.worker.jobs import plan_expirer, plan_generator, reporter
from packages.ops.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def main():
    """Main worker function."""
    scheduler = BlockingScheduler()

    # Plan generator: daily at 9:00 AM KST
    scheduler.add_job(
        plan_generator.run,
        trigger=CronTrigger(hour=9, minute=0, timezone="Asia/Seoul"),
        id="plan_generator",
        name="Generate rebalance plans",
    )

    # Plan expirer: hourly
    scheduler.add_job(
        plan_expirer.run,
        trigger=CronTrigger(minute=0),
        id="plan_expirer",
        name="Expire old plans",
    )

    # Reporter: daily at 6:00 PM KST
    scheduler.add_job(
        reporter.run,
        trigger=CronTrigger(hour=18, minute=0, timezone="Asia/Seoul"),
        id="reporter",
        name="Generate daily report",
    )

    logger.info("Worker started with scheduled jobs")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped")


if __name__ == "__main__":
    main()
