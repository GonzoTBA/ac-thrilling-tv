"""User interface helpers for the ACTTV app."""

import time
import ac

from . import config, state
from .scheduler import schedule_next_switch

# ctypes may not be available in AC's embedded Python; load lazily and guard
try:
    import ctypes as _ctypes  # type: ignore
except Exception:
    _ctypes = None


def ctypes_available():
    return _ctypes is not None


def update_ui():
    """Refresh labels and button text."""
    now = time.time()
    remaining = state.next_switch_time - now
    if remaining < 0.0:
        remaining = 0.0

    if state.status_label is not None:
        ac.setText(state.status_label, "{} | next: {:0.1f}s".format("running" if state.enabled else "paused", remaining))

    if state.camera_label is not None:
        ac.setText(state.camera_label, "Camera: TV/manual (set with F2/F5/F6) | Mode: Proximity")

    if state.toggle_button is not None:
        ac.setText(state.toggle_button, "Pause" if state.enabled else "Resume")

    if getattr(state, "force_tv_button", None) is not None:
        if ctypes_available():
            ac.setText(state.force_tv_button, "Force TV cam")
            try:
                ac.setFontColor(state.force_tv_button, 1.0, 1.0, 1.0, 1.0)
            except Exception:
                pass
        else:
            ac.setText(state.force_tv_button, "Force TV cam (N/A)")
            try:
                ac.setFontColor(state.force_tv_button, 0.6, 0.6, 0.6, 1.0)
            except Exception:
                pass

    if getattr(state, "force_tv_status_label", None) is not None:
        status = "available" if ctypes_available() else "unavailable"
        ac.setText(state.force_tv_status_label, "Force TV: {}".format(status))


def toggle_callback(*args):
    """Pause/Resume button callback."""
    state.enabled = not state.enabled
    ac.log("[{}] Button pressed. Now: {}".format(config.APP_NAME, "enabled" if state.enabled else "paused"))
    if state.enabled:
        schedule_next_switch()
    update_ui()


def force_tv_cam(*args):
    """Force switch to TV camera by simulating the F6 key.

    If `_ctypes` is unavailable in this environment, the feature is
    disabled gracefully and we log a message for troubleshooting.
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
        # Press F6 (VK_F6 = 0x75)
        user32.keybd_event(0x75, 0, 0, 0)
        # Release
        user32.keybd_event(0x75, 0, 2, 0)
    except Exception:
        log("ui.py: exception using ctypes to send F6")
        # Silently ignore to avoid breaking the app
