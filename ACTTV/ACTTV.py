"""Assetto Corsa app entry points."""

import time
import ac

from . import config, state
from .focus import focus_best_by_proximity
from .scheduler import schedule_next_switch
from .ui import toggle_callback, update_ui


def acMain(ac_version):
    ac.log("[{}] acMain called".format(config.APP_NAME))

    state.app_window = ac.newApp(config.APP_NAME)
    ac.setTitle(state.app_window, config.APP_NAME)
    ac.setSize(state.app_window, 340, 130)

    state.status_label = ac.addLabel(state.app_window, "starting…")
    ac.setPosition(state.status_label, 10, 30)

    state.toggle_button = ac.addButton(state.app_window, "Pause")
    ac.setPosition(state.toggle_button, 10, 55)
    ac.setSize(state.toggle_button, 120, 25)
    ac.addOnClickedListener(state.toggle_button, toggle_callback)

    state.camera_label = ac.addLabel(state.app_window, "Camera: TV/manual (set with F2/F5/F6) | Mode: Proximity")
    ac.setPosition(state.camera_label, 10, 85)

    schedule_next_switch()
    update_ui()

    return config.APP_NAME


def acUpdate(deltaT):
    now = time.time()

    if state.enabled and now >= state.next_switch_time:
        focus_best_by_proximity()
        schedule_next_switch(now)

    update_ui()

