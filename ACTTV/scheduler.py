"""Timing helpers for switching camera focus."""

import random
import time
import ac

from . import config, state


def schedule_next_switch(now=None):
    """Schedule the next camera switch with jitter."""
    if now is None:
        now = time.time()
    interval = config.BASE_INTERVAL + random.uniform(-config.JITTER, config.JITTER)
    if interval < 3.0:
        interval = 3.0
    state.next_switch_time = now + interval
    ac.log("[{}] Next switch scheduled in {:.1f}s".format(config.APP_NAME, interval))

