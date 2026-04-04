import subprocess
import os
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = BlockingScheduler()

def run_spider():
    print(f"\n🕷️  Running spider at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        ["scrapy", "crawl", "amazon_bearing"],
        cwd=project_root,
        capture_output=False
    )
    if result.returncode == 0:
        print(f"✅ Spider completed at {datetime.now().strftime('%H:%M:%S')}")
    else:
        print(f"❌ Spider failed with code {result.returncode}")

def start_scheduler(interval_minutes=60):
    print(f"\n{'='*55}")
    print(f"  Scheduler started — runs every {interval_minutes} minutes")
    print(f"  First run: NOW")
    print(f"  Press Ctrl+C to stop")
    print(f"{'='*55}\n")

    scheduler.add_job(
        run_spider,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="amazon_spider",
        next_run_time=datetime.now(),
        max_instances=1,
    )

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n⛔ Scheduler stopped.")
        scheduler.shutdown()

if __name__ == "__main__":
    start_scheduler(interval_minutes=60)