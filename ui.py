"""User interface helpers for the ACTTV app."""

import time
import ac

from . import config, state
from .scheduler import schedule_next_switch, get_race_intensity

# ctypes may not be available in AC's embedded Python; load lazily and guard
try:
    import ctypes as _ctypes  # type: ignore
except Exception as ex:
    _ctypes = None
    # Log the exact import failure for diagnosis
    try:
        ac.log("[{}] ctypes import failed: {}".format(config.APP_NAME, ex))
    except Exception:
        pass


def ctypes_available():
    return _ctypes is not None


def update_ui():
    """Refresh labels and button text."""
    now = time.time()
    remaining = state.next_switch_time - now
    if remaining < 0.0:
        remaining = 0.0

    if state.status_label is not None:
        ac.setText(state.status_label, "{} | next: {:0.1f}s | Intensity: {:0.2f}".format(
            "running" if state.enabled else "paused", remaining, get_race_intensity()
        ))

    if state.toggle_button is not None:
        ac.setText(state.toggle_button, "Pause" if state.enabled else "Resume")

    if getattr(state, "force_tv_button", None) is not None:
        ac.setText(state.force_tv_button, "Force TV cam")

    # Focus info: current car id and reason
    if getattr(state, "focus_label", None) is not None:
        car_id = state.current_focus()
        reason = state.current_reason() if hasattr(state, "current_reason") else ""
        if car_id is None or car_id < 0:
            ac.setText(state.focus_label, "Focus: — | Reason: —")
        else:
            ac.setText(state.focus_label, "Focus: car {} | Reason: {}".format(car_id, reason or ""))


def toggle_callback(*args):
    """Pause/Resume button callback."""
    state.enabled = not state.enabled
    ac.log("[{}] Button pressed. Now: {}".format(config.APP_NAME, "enabled" if state.enabled else "paused"))
    if state.enabled:
        schedule_next_switch()
    update_ui()


def force_tv_cam(*args):
    """Force switch to TV camera by simulating the F3 key.

    Requires `ctypes` availability in Assetto Corsa's Python.
    """
    if _ctypes is None:
        try:
            ac.log("[{}] ctypes unavailable; Force TV disabled".format(config.APP_NAME))
        except Exception:
            pass
        return

    try:
        ac.log("[{}] Forcing TV camera".format(config.APP_NAME))
        user32 = _ctypes.windll.user32
        # Press F3 (VK_F3 = 0x72)
        user32.keybd_event(0x72, 0, 0, 0)
        # Release
        user32.keybd_event(0x72, 0, 2, 0)
    except Exception:
        try:
            ac.log("[{}] ctypes F3 send failed".format(config.APP_NAME))
        except Exception:
            pass
        # Silently ignore to avoid breaking the app
