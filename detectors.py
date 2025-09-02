"""Event detectors: collision, spin, offtrack, pit_entry."""

import time
from . import config, state
from . import spatial
from .logging_utils import log


class Event(object):
    def __init__(self, car_id, etype, severity, t_expires):
        self.car_id = car_id
        self.type = etype
        self.severity = severity
        self.t_expires = t_expires


# Cooldowns to avoid repeat triggers per car
_last_event_t = {
    "collision": {},  # car_id -> t
    "offtrack": {},
}


def _cooldown_ok(etype, car_id, now):
    cd = 0.0
    if etype == "collision":
        cd = getattr(config, "COLLISION_COOLDOWN_S", 2.0)
    elif etype == "offtrack":
        cd = getattr(config, "OFFTRACK_COOLDOWN_S", 2.0)
    last = _last_event_t.get(etype, {}).get(car_id, 0.0)
    return (now - last) >= cd


def _mark_event(etype, car_id, now):
    try:
        _last_event_t.setdefault(etype, {})[car_id] = now
    except Exception:
        pass


def _recent_delta_speed(i, window):
    hist = state.speed_hist(i)
    if len(hist) < 2:
        return 0.0, 0.0, 0.0, 0.0
    t_now = hist[-1][0]
    s_now = hist[-1][1]
    # find sample older than window
    s_then = s_now
    t_then = t_now
    for k in range(len(hist) - 2, -1, -1):
        t, s = hist[k]
        if t_now - t >= window:
            s_then = s
            t_then = t
            break
        s_then = s
        t_then = t
    dt = max(0.0001, t_now - t_then)
    return (s_then - s_now), dt, s_then, s_now


def _recent_yaw_rate(i):
    hist = state.yaw_hist(i)
    if len(hist) == 0:
        return 0.0
    return hist[-1][1]


def _avg_abs_yaw(i, window):
    hist = state.yaw_hist(i)
    if not hist:
        return 0.0
    t_now = hist[-1][0]
    t_min = t_now - window
    s = 0.0
    k = 0
    for t, y in reversed(hist):
        if t < t_min:
            break
        s += abs(y)
        k += 1
    if k == 0:
        return abs(hist[-1][1])
    return s / float(k)


def _pit_transition(i):
    # Approximate pit_entry: in_pitlane or in_pit transitions
    # Heuristic: if current is True and last 1-2 samples were False
    # We reuse speed history timestamps as we do not track pit flags history explicitly
    # Keep simple: trigger when entering pitlane now and speed small
    try:
        in_lane = state._in_pitlane[i]
        in_pit = state._in_pit[i]
    except Exception:
        return False
    if not in_lane and not in_pit:
        return False
    sp = state.speed_kmh(i)
    return sp < 60.0


def scan(st, now):
    """Scan events and return prioritized list.

    Returns: [Event]
    """
    events = []
    n = st.car_count()
    grid = spatial.build_grid(st, config.CELL_SIZE_M)
    # Pending offtrack confirmation per-car
    if not hasattr(scan, "_pending_offtrack"):
        scan._pending_offtrack = {}
    if not hasattr(scan, "_pending_collision"):
        scan._pending_collision = {}

    for i in range(n):
        # Skip near-stationary cars if configured
        sp = st.speed_kmh(i)
        if config.IGNORE_STOPPED_CARS and sp <= config.STOPPED_SPEED_KMH:
            continue

        # Collision: strong decel with minimum real window, nearby rival, and persistence
        drop, dt, spre, snow = _recent_delta_speed(i, config.COLLISION_WINDOW_S)
        yaw = _recent_yaw_rate(i)
        if dt > 0.0:
            decel_rate = drop / dt  # km/h per second
        else:
            decel_rate = 0.0
        ratio = (drop / max(1.0, spre)) if spre > 0.0 else 0.0

        # Nearest distance check
        pi = st.pos(i)
        nearest_d = 1e9
        if pi is not None:
            for j in spatial.neighbors_of(i, pi, grid):
                pj = st.pos(j)
                if pj is None:
                    continue
                dx = pi[0] - pj[0]
                dz = pi[2] - pj[2]
                d2 = dx * dx + dz * dz
                if d2 < nearest_d * nearest_d:
                    import math
                    nearest_d = math.sqrt(d2)

        base_ok = (
            dt >= getattr(config, "COLLISION_MIN_DT_S", 0.18)
            and drop >= config.COLLISION_MIN_DROP_KMH
            and spre >= config.COLLISION_MIN_PRE_SPEED_KMH
            and ratio >= getattr(config, "COLLISION_MIN_DROP_RATIO", 0.3)
            and decel_rate >= config.COLLISION_MIN_DECEL_KMH_S
            and snow <= getattr(config, "COLLISION_MAX_POST_SPEED_KMH", 55.0)
            and nearest_d <= getattr(config, "COLLISION_NEAR_RADIUS_M", 7.0)
            and not st._in_pit[i]
        )

        if base_ok and _cooldown_ok("collision", i, now):
            first_c = scan._pending_collision.get(i)
            if first_c is None:
                scan._pending_collision[i] = now
            else:
                if (now - first_c) <= getattr(config, "COLLISION_CONFIRM_WINDOW_S", 0.2):
                    sev = min(1.0, max(drop / 60.0, decel_rate / 250.0) * (1.0 + 0.2 * max(0.0, yaw - 0.5)))
                    ev = Event(i, "collision", sev, now + 2.5)
                    events.append(ev)
                    _mark_event("collision", i, now)
                    scan._pending_collision.pop(i, None)
                    log("event collision car={} dV={:.1f} rate={:.0f} near={:.1f} yaw={:.2f}".format(i, drop, decel_rate, nearest_d, yaw))
                    continue
                else:
                    scan._pending_collision.pop(i, None)
        else:
            if i in scan._pending_collision:
                scan._pending_collision.pop(i, None)

        # Spin: low speed and high yaw rate
        if sp <= 35.0 and yaw >= 1.5:  # rad/s heuristic
            ev = Event(i, "spin", min(1.0, yaw / 3.0), now + 3.0)
            events.append(ev)
            log("event spin car={} yaw={:.2f}".format(i, yaw))
            continue

        # Offtrack: significant speed drop, not in pit, yaw moderate and sustained.
        drop2, dt2, spre2, snow2 = _recent_delta_speed(i, config.OFFTRACK_WINDOW_S)
        ratio2 = (drop2 / max(1.0, spre2)) if spre2 > 0.0 else 0.0
        yaw_avg = _avg_abs_yaw(i, min(0.5, config.OFFTRACK_WINDOW_S))
        base_ok = (
            dt2 > 0.0
            and not st._in_pit[i]
            and spre2 >= config.OFFTRACK_MIN_PRE_SPEED_KMH
            and drop2 >= config.OFFTRACK_MIN_DROP_KMH
            and config.OFFTRACK_MIN_NOW_SPEED_KMH <= snow2 <= config.OFFTRACK_MAX_NOW_SPEED_KMH
            and config.OFFTRACK_YAW_MIN_RAD_S <= yaw <= config.OFFTRACK_YAW_MAX_RAD_S
            and yaw_avg >= getattr(config, "OFFTRACK_AVG_YAW_MIN_RAD_S", 0.25)
            and config.OFFTRACK_MIN_DROP_RATIO <= ratio2 <= config.OFFTRACK_MAX_DROP_RATIO
        )

        if base_ok and _cooldown_ok("offtrack", i, now):
            first = scan._pending_offtrack.get(i)
            if first is None:
                # Stage 1: mark and wait confirmation
                scan._pending_offtrack[i] = now
            else:
                # Confirm within window with conditions still true
                if (now - first) <= getattr(config, "OFFTRACK_CONFIRM_WINDOW_S", 0.3):
                    ev = Event(i, "offtrack", min(1.0, drop2 / 60.0), now + 2.0)
                    events.append(ev)
                    _mark_event("offtrack", i, now)
                    scan._pending_offtrack.pop(i, None)
                    log("event offtrack car={} drop={:.1f} yaw={:.2f} yaw_avg={:.2f}".format(i, drop2, yaw, yaw_avg))
                    continue
                else:
                    # Expired pending; reset
                    scan._pending_offtrack.pop(i, None)
        else:
            # Conditions not met; clear any pending flag for this car
            if i in scan._pending_offtrack:
                scan._pending_offtrack.pop(i, None)

        # Pit entry heuristic
        if _pit_transition(i):
            ev = Event(i, "pit_entry", 0.3, now + 2.0)
            events.append(ev)

    if not events:
        return []

    # priority: collision > spin > offtrack > pit_entry
    prio = {"collision": 0, "spin": 1, "offtrack": 2, "pit_entry": 3}
    events.sort(key=lambda e: (prio.get(e.type, 99), -e.severity))
    # filter by TTL (though all are fresh)
    now_t = now
    events = [e for e in events if e.t_expires > now_t]
    return events
