"""Scheduling utilities for natural dwell and event dwell."""

import random
import time
import ac

from . import config, state


_race_intensity = 0.0
_lock_until = 0.0
_next_natural_deadline = 0.0


def _natural_interval():
    base = config.DWELL_BASE
    jitter = random.uniform(-config.JITTER_RANGE, config.JITTER_RANGE)
    # Adapt by race intensity
    k = config.K_INTENSITY
    low_bonus = getattr(config, "LOW_INTENSITY_BONUS", 0.0)
    # Longer shots when intensity is low; shorter when high
    # Base factor combining low-intensity bonus and linear reduction by intensity
    factor = 1.0 + low_bonus * (1.0 - _race_intensity) - k * _race_intensity
    # Additional shortening up to 20% at max intensity
    shorten_max = getattr(config, "HIGH_INTENSITY_SHORTEN_MAX", 0.20)
    factor *= (1.0 - shorten_max * _race_intensity)
    if factor < 0.3:
        factor = 0.3
    interval = base * factor + jitter
    if interval < 3.0:
        interval = 3.0
    return interval


def set_race_intensity(value):
    global _race_intensity
    if value < 0.0:
        value = 0.0
    if value > 1.0:
        value = 1.0
    _race_intensity = value


def get_race_intensity():
    return _race_intensity


def on_switch(now, reason):
    """Register a switch and program next deadlines.

    reason: "natural" or event type (collision/spin/offtrack/pit_entry)
    """
    global _lock_until, _next_natural_deadline

    # Program event dwell lock
    dwell = 0.0
    if reason == "collision":
        dwell = config.EVENT_DWELL_COLLISION
    elif reason == "spin":
        dwell = config.EVENT_DWELL_SPIN
    elif reason == "offtrack":
        dwell = config.EVENT_DWELL_OFFTRACK
    elif reason == "pit_entry":
        dwell = config.EVENT_DWELL_PIT_ENTRY
    else:
        dwell = 0.0

    if dwell > 0.0:
        _lock_until = now + dwell
    else:
        # No event lock
        if _lock_until < now:
            _lock_until = 0.0

    # Always schedule a natural deadline after a switch
    interval = _natural_interval()
    _next_natural_deadline = now + interval
    try:
        ac.log("[{}] on_switch: reason={} lock_until={:.1f} next_natural+{:.1f}s".format(
            config.APP_NAME, reason, _lock_until, interval
        ))
    except Exception:
        pass

    state.next_switch_time = _next_natural_deadline


def should_natural_switch(now):
    return now >= _next_natural_deadline


def next_natural_deadline():
    return _next_natural_deadline


def lock_until():
    return _lock_until


def is_locked(now):
    return now < _lock_until


def schedule_next_switch(now=None):
    """Compatibility helper for existing UI button logic."""
    if now is None:
        now = time.time()
    interval = _natural_interval()
    global _next_natural_deadline
    _next_natural_deadline = now + interval
    state.next_switch_time = _next_natural_deadline
    try:
        ac.log("[{}] Next natural switch in {:.1f}s".format(config.APP_NAME, interval))
    except Exception:
        pass
