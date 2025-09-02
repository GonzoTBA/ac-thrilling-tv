"""Assetto Corsa app entry points."""

import time
import ac

try:
    from . import config, state
    from .detectors import scan as scan_events
    from .interest import pick_best_by_interest
    from .focus import maybe_focus_event, switch_to
    from .scheduler import (
        schedule_next_switch,
        should_natural_switch,
        on_switch,
        is_locked,
    )
    from .ui import toggle_callback, force_tv_cam, update_ui, ctypes_available
except Exception as ex:
    ac.log("[ACTTV] Import error: {}".format(ex))
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

        # Focus info label: current car and reason
        state.focus_label = ac.addLabel(state.app_window, "Focus: — | Reason: —")
        ac.setPosition(state.focus_label, 10, 130)
        ac.log("[{}] Focus label added".format(config.APP_NAME))

        schedule_next_switch()
        ac.log("[{}] Next switch scheduled".format(config.APP_NAME))
        # Initial focus to leader at race start
        try:
            now = time.time()
            state.update_snapshot(now)
            n = state.car_count()
            if n > 0:
                # Pick highest spline as leader
                ranks = sorted([(state.spline(c), c) for c in range(n)], reverse=True)
                leader = ranks[0][1]
                if leader >= 0:
                    if switch_to(leader, now, "start_leader"):
                        on_switch(now, "start_leader")
        except Exception as ex:
            ac.log("[{}] Initial leader focus failed: {}".format(config.APP_NAME, ex))

        update_ui()
        ac.log("[{}] UI initialized".format(config.APP_NAME))
    except Exception as ex:
        ac.log("[{}] Exception in acMain: {}".format(config.APP_NAME, ex))
        raise

    return config.APP_NAME


def acUpdate(deltaT):
    try:
        now = time.time()

        # 1) Update snapshot
        state.update_snapshot(now)

        # 1b) At start lights phase, focus leader once
        try:
            if not state.start_leader_done:
                n = state.car_count()
                if n > 0:
                    stopped_grid = 0
                    for i in range(n):
                        sp = state.speed_kmh(i)
                        if sp <= max(2.0, getattr(config, "STOPPED_SPEED_KMH", 1.0) + 1.0) and (not state._in_pit[i]) and (not state._in_pitlane[i]):
                            stopped_grid += 1
                    if stopped_grid >= max(2, int(0.6 * n)):
                        ranks = sorted([(state.spline(c), c) for c in range(n)], reverse=True)
                        leader = ranks[0][1]
                        if leader >= 0:
                            if switch_to(leader, now, "start_lights_leader"):
                                on_switch(now, "start_lights_leader")
                                state.start_leader_done = True
        except Exception as ex:
            ac.log("[{}] Start lights leader focus check failed: {}".format(config.APP_NAME, ex))

        # 2) Detect events
        events = scan_events(state, now)

        # 3) Event interrupt if not locked
        if state.enabled and (not is_locked(now)) and events:
            if maybe_focus_event(events, now):
                on_switch(now, events[0].type)
                update_ui()
                return

        # 4) Natural switch
        if state.enabled and should_natural_switch(now):
            car = pick_best_by_interest(state, now)
            if car >= 0:
                if switch_to(car, now, "natural"):
                    on_switch(now, "natural")

        # 5) UI
        update_ui()
    except Exception as ex:
        ac.log("[{}] Exception in acUpdate: {}".format(config.APP_NAME, ex))
        raise


def acShutdown():
    try:
        ac.log("[{}] acShutdown called".format(config.APP_NAME))
    except Exception:
        pass
    return
