"""Focus orchestration: events + natural switches with guards."""

import ac
from . import config, state
from .logging_utils import log


def switch_to(car_id, now, reason):
    if car_id < 0:
        return False
    current = state.current_focus()
    if current == car_id and reason == "natural":
        return False
    try:
        ac.focusCar(car_id)
        state.set_current_focus(car_id, now)
        state.set_current_reason(reason)
        log("Focus -> car {} (reason={})".format(car_id, reason))
        return True
    except Exception as ex:
        log("focusCar failed: {}".format(ex))
        return False


def maybe_focus_event(events, now):
    if not events:
        return False
    # events are pre-sorted by priority
    target = events[0].car_id
    # Avoid switching to near-stationary cars on events
    try:
        from . import config, state
        if state.speed_kmh(target) <= getattr(config, "MIN_FOCUS_SPEED_KMH", 0.0):
            return False
    except Exception:
        pass
    return switch_to(target, now, events[0].type)
