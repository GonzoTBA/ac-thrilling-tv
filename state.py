"""Shared state and live snapshot buffers for ACTTV."""

import time
import ac
import acsys

# --- UI / state ---
app_window = None
status_label = None
camera_label = None
focus_label = None
toggle_button = None
force_tv_button = None
force_tv_status_label = None

next_switch_time = 0.0
_current_car_id = -1
_current_reason = ""
enabled = True
start_leader_done = False

# --- Live snapshot per car ---
_last_update_t = 0.0
_car_count = 0

_pos = []           # (x, y, z)
_speed_kmh = []     # float
_vel = []           # (vx, vy, vz) or None
_spline = []        # float
_lap = []           # int
_in_pit = []        # bool
_in_pitlane = []    # bool

# ring buffers short (store last 10)
_speed_hist = []    # list[list[(t, speed_kmh)]]
_yaw_hist = []      # list[list[(t, yaw_rate)]]
_last_heading = []  # last heading radians (-pi..pi)

# focus bookkeeping
_last_focused_at = []  # timestamps per car
_unseen_set = set()    # car ids that never got focus yet

# stepping for proximity
_prox_scan_index = 0


def car_count():
    return _car_count


def active(i):
    try:
        if _speed_kmh[i] is None:
            return False
        if ac.isCarInPit(i) == 1:
            return False
        if _speed_kmh[i] < 1.0:
            return False
        return True
    except Exception:
        return False


def pos(i):
    if 0 <= i < _car_count:
        return _pos[i]
    return None


def speed_kmh(i):
    if 0 <= i < _car_count:
        return _speed_kmh[i]
    return 0.0


def spline(i):
    if 0 <= i < _car_count:
        return _spline[i]
    return 0.0


def update_snapshot(now):
    global _last_update_t, _car_count, _prox_scan_index
    _last_update_t = now
    n = ac.getCarsCount()
    if n != _car_count:
        _resize(n)
    _car_count = n

    for i in range(n):
        try:
            p = ac.getCarState(i, acsys.CS.WorldPosition)
        except Exception:
            p = None
        try:
            sp = ac.getCarState(i, acsys.CS.SpeedKMH)
        except Exception:
            sp = 0.0
        try:
            v = ac.getCarState(i, acsys.CS.Velocity)
        except Exception:
            v = None
        try:
            s = ac.getCarState(i, acsys.CS.NormalizedSplinePosition)
        except Exception:
            s = 0.0
        try:
            lap = ac.getCarState(i, acsys.CS.LapCount)
        except Exception:
            lap = 0
        try:
            pit = ac.isCarInPit(i) == 1
        except Exception:
            pit = False
        try:
            pitl = ac.isCarInPitlane(i) == 1
        except Exception:
            # Older AC uses different name; fall back to false if not found
            try:
                pitl = ac.isCarInPitLane(i) == 1
            except Exception:
                pitl = False

        _pos[i] = p
        _speed_kmh[i] = sp
        _vel[i] = v
        _spline[i] = s
        _lap[i] = lap
        _in_pit[i] = pit
        _in_pitlane[i] = pitl

        _update_ring_buffers(i, now)

    if not _unseen_set and n > 0 and all(t > 0.0 for t in _last_focused_at[:n]) is False:
        # Initialize unseen set once at start
        _unseen_set.update(range(n))

    # wrap scan index
    if _prox_scan_index >= n:
        _prox_scan_index = 0


def _resize(n):
    # Resize all arrays to size n
    def grow(arr, fill):
        while len(arr) < n:
            arr.append(fill)
        while len(arr) > n:
            arr.pop()

    grow(_pos, None)
    grow(_speed_kmh, 0.0)
    grow(_vel, None)
    grow(_spline, 0.0)
    grow(_lap, 0)
    grow(_in_pit, False)
    grow(_in_pitlane, False)

    grow(_speed_hist, [])
    grow(_yaw_hist, [])
    grow(_last_heading, 0.0)
    grow(_last_focused_at, 0.0)


def _update_ring_buffers(i, now):
    # Speed history
    sh = _speed_hist[i]
    if sh is None:
        sh = []
        _speed_hist[i] = sh
    sh.append((now, _speed_kmh[i]))
    if len(sh) > 10:
        del sh[0:len(sh) - 10]

    # Heading and yaw-rate from velocity (XZ plane)
    try:
        v = _vel[i]
        if v is not None:
            vx, vy, vz = v
            if vx != 0.0 or vz != 0.0:
                import math

                heading = math.atan2(vz, vx)
                prev = _last_heading[i]
                dt = 0.0
                if prev is None:
                    yaw_rate = 0.0
                else:
                    # unwrap small angle diff
                    diff = heading - prev
                    while diff > math.pi:
                        diff -= 2.0 * math.pi
                    while diff < -math.pi:
                        diff += 2.0 * math.pi
                    # estimate dt from last speed sample
                    if len(_speed_hist[i]) >= 2:
                        dt = _speed_hist[i][-1][0] - _speed_hist[i][-2][0]
                    if dt <= 0.0:
                        dt = 0.016
                    yaw_rate = abs(diff) / dt
                _last_heading[i] = heading
            else:
                yaw_rate = 0.0
        else:
            yaw_rate = 0.0
    except Exception:
        yaw_rate = 0.0

    yh = _yaw_hist[i]
    if yh is None:
        yh = []
        _yaw_hist[i] = yh
    yh.append((now, yaw_rate))
    if len(yh) > 10:
        del yh[0:len(yh) - 10]


def set_current_focus(i, now):
    global _current_car_id
    _current_car_id = i
    if 0 <= i < len(_last_focused_at):
        _last_focused_at[i] = now
    mark_seen(i)


def current_focus():
    return _current_car_id


def set_current_reason(reason):
    global _current_reason
    _current_reason = reason or ""


def current_reason():
    return _current_reason


def last_focused_at(i):
    if 0 <= i < len(_last_focused_at):
        return _last_focused_at[i]
    return 0.0


def unseen_set():
    return set(_unseen_set)


def mark_seen(i):
    try:
        if i in _unseen_set:
            _unseen_set.discard(i)
    except Exception:
        pass


def speed_hist(i):
    return _speed_hist[i] if 0 <= i < len(_speed_hist) else []


def yaw_hist(i):
    return _yaw_hist[i] if 0 <= i < len(_yaw_hist) else []


def prox_scan_index():
    return _prox_scan_index


def bump_prox_scan_index(step):
    global _prox_scan_index
    if _car_count <= 0:
        _prox_scan_index = 0
    else:
        _prox_scan_index = (_prox_scan_index + step) % _car_count
