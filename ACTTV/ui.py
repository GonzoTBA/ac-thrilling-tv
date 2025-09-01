"""User interface helpers for the ACTTV app."""

import time
import ctypes
import ac

from . import config, state
from .scheduler import schedule_next_switch


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
        ac.setText(state.force_tv_button, "Force TV cam")


def toggle_callback(*args):
    """Pause/Resume button callback."""
    state.enabled = not state.enabled
    ac.log("[{}] Button pressed. Now: {}".format(config.APP_NAME, "enabled" if state.enabled else "paused"))
    if state.enabled:
        schedule_next_switch()
    update_ui()


def force_tv_cam(*args):
    """Force switch to TV camera by simulating the F6 key."""
    ac.log("[{}] Forcing TV camera".format(config.APP_NAME))
    user32 = ctypes.windll.user32
    # Press
    user32.keybd_event(0x75, 0, 0, 0)
    # Release
    user32.keybd_event(0x75, 0, 2, 0)

