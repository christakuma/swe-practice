"""The invoice worker: takes a job, processes it, takes the next.

The queue is a stand-in -- each job is a one-second sleep -- but the shutdown
handling is real. On SIGTERM it finishes the job in hand and exits, which is
the whole point of having a handler: nothing is left half-written.
"""

import signal
import threading
import time

stopping = threading.Event()


def stop(_signum: int, _frame: object) -> None:
    print("SIGTERM received: finishing the current job, then exiting", flush=True)
    stopping.set()


signal.signal(signal.SIGTERM, stop)
print("worker started", flush=True)

job = 0
while not stopping.is_set():
    job += 1
    print(f"processing invoice batch {job}", flush=True)
    time.sleep(1)

print("worker stopped cleanly", flush=True)
