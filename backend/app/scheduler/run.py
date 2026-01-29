"""Standalone scheduler process entry point.

Run with: python -m app.scheduler.run
"""

import asyncio
import signal

from app.scheduler.manager import create_scheduler


async def main():
    scheduler = create_scheduler()
    scheduler.start()
    print("[Scheduler] Started. Press Ctrl+C to exit.")

    stop_event = asyncio.Event()

    def signal_handler():
        stop_event.set()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)

    await stop_event.wait()
    scheduler.shutdown()
    print("[Scheduler] Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
