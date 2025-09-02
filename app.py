"""Assetto Corsa app entry points."""

import time
import ac

ac.log("[ACTTV] Module import beginning")
try:
    from . import config, state
    from .focus import focus_best_by_proximity
    from .scheduler import schedule_next_switch
    from .ui import toggle_callback, force_tv_cam, update_ui, ctypes_available
    ac.log("[ACTTV] Submodules imported successfully")
except Exception as ex:
    ac.log("[ACTTV] Error importing submodules: {}".format(ex))
    raise


def acMain(ac_version):
    ac.log("[{}] acMain called (version: {})".format(config.APP_NAME, ac_version))
    try:
        state.app_window = ac.newApp(config.APP_NAME)
        ac.setTitle(state.app_window, config.APP_NAME)
        ac.setSize(state.app_window, 340, 150)
        ac.log("[{}] App window created".format(config.APP_NAME))

        state.status_label = ac.addLabel(state.app_window, "starting…")
        ac.setPosition(state.status_label, 10, 30)
        ac.log("[{}] Status label added".format(config.APP_NAME))

        state.toggle_button = ac.addButton(state.app_window, "Pause")
        ac.setPosition(state.toggle_button, 10, 55)
        ac.setSize(state.toggle_button, 120, 25)
        ac.addOnClickedListener(state.toggle_button, toggle_callback)
        ac.log("[{}] Toggle button added".format(config.APP_NAME))

        state.force_tv_button = ac.addButton(state.app_window, "Force TV cam")
        ac.setPosition(state.force_tv_button, 140, 55)
        ac.setSize(state.force_tv_button, 120, 25)
        if ctypes_available():
            ac.addOnClickedListener(state.force_tv_button, force_tv_cam)
        ac.log("[{}] Force TV button added".format(config.APP_NAME))

        state.camera_label = ac.addLabel(
            state.app_window,
            "Camera: TV/manual (set with F2/F5/F6) | Mode: Proximity",
        )
        ac.setPosition(state.camera_label, 10, 85)
        ac.log("[{}] Camera label added".format(config.APP_NAME))

        # Small indicator for Force TV availability
        state.force_tv_status_label = ac.addLabel(state.app_window, "")
        ac.setPosition(state.force_tv_status_label, 10, 110)
        ac.log("[{}] Force TV status label added".format(config.APP_NAME))

        schedule_next_switch()
        ac.log("[{}] Next switch scheduled".format(config.APP_NAME))
        update_ui()
        ac.log("[{}] UI initialized".format(config.APP_NAME))
    except Exception as ex:
        ac.log("[{}] Exception in acMain: {}".format(config.APP_NAME, ex))
        raise

    return config.APP_NAME


def acUpdate(deltaT):
    ac.log("[{}] acUpdate called (deltaT: {:0.3f})".format(config.APP_NAME, deltaT))
    try:
        now = time.time()

        if state.enabled and now >= state.next_switch_time:
            ac.log("[{}] Attempting to switch focus".format(config.APP_NAME))
            focus_best_by_proximity()
            schedule_next_switch(now)

        update_ui()
        ac.log("[{}] UI updated".format(config.APP_NAME))
    except Exception as ex:
        ac.log("[{}] Exception in acUpdate: {}".format(config.APP_NAME, ex))
        raise


def acShutdown():
    try:
        ac.log("[{}] acShutdown called".format(config.APP_NAME))
    except Exception:
        pass
    return
