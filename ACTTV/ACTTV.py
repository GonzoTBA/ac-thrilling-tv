import ac
import acsys
import random
import time
import math

APP_NAME = "ACTTV"

# --- Config ---
BASE_INTERVAL = 10.0     # base seconds between switches
JITTER = 3.0             # random +/- seconds
MIN_CARS_REQUIRED = 1
NEAR_RADIUS_M = 20.0     # proximity radius (meters) for "battle" scoring

# --- UI / state ---
app_window = None
status_label = None
camera_label = None
toggle_button = None

next_switch_time = 0.0
current_car_id = -1
enabled = True


# ---------- Helpers ----------
def schedule_next_switch(now=None):
    """Schedule the next camera switch with jitter."""
    global next_switch_time
    if now is None:
        now = time.time()
    interval = BASE_INTERVAL + random.uniform(-JITTER, JITTER)
    if interval < 3.0:
        interval = 3.0
    next_switch_time = now + interval
    ac.log("[{}] Next switch scheduled in {:.1f}s".format(APP_NAME, interval))


def get_world_pos(car_id):
    """Return (x, y, z) world position or None on error."""
    try:
        return ac.getCarState(car_id, acsys.CS.WorldPosition)
    except:
        return None


def distance_sq(p1, p2):
    """Squared distance in XZ-plane (ignore height)."""
    dx = p1[0] - p2[0]
    dz = p1[2] - p2[2]
    return dx * dx + dz * dz


def is_car_active(car_id):
    """Filter cars we don't want to focus (pits or stopped)."""
    try:
        if ac.isCarInPit(car_id) == 1:
            return False
        if ac.getCarState(car_id, acsys.CS.SpeedKMH) < 1.0:
            return False
        return True
    except:
        return False


def pick_best_car_by_proximity():
    """
    Score each active car by how many rivals are within NEAR_RADIUS_M
    (and slightly by how close they are). Return best car_id or None.
    """
    car_count = ac.getCarsCount()
    if car_count < MIN_CARS_REQUIRED:
        return None

    # Cache positions and active flags
    positions = [get_world_pos(i) for i in range(car_count)]
    actives = [is_car_active(i) and (positions[i] is not None) for i in range(car_count)]

    best_car = None
    best_score = -1.0
    near_r2 = NEAR_RADIUS_M * NEAR_RADIUS_M

    for i in range(car_count):
        if not actives[i]:
            continue
        pi = positions[i]
        score = 0.0
        close_count = 0

        for j in range(car_count):
            if i == j or not actives[j]:
                continue
            pj = positions[j]
            d2 = distance_sq(pi, pj)
            if d2 <= near_r2:
                # +1 per car inside radius, with a tiny bonus for being closer
                close_count += 1
                # Avoid division by zero; add small epsilon
                score += 1.0 + (0.5 / (1.0 + d2))

        # Prefer cars with more close rivals; tie-breaker: avoid repeating current
        if score > best_score or (score == best_score and i != current_car_id):
            best_score = score
            best_car = i

    # Fallback: if no "close" battles found, at least return a valid active car
    if best_car is None:
        for i in range(car_count):
            if actives[i]:
                best_car = i
                break

    return best_car


def focus_best_by_proximity():
    """Focus the car selected by proximity scoring."""
    global current_car_id
    target = pick_best_car_by_proximity()
    if target is None:
        ac.log("[{}] No suitable target (proximity).".format(APP_NAME))
        return False
    try:
        ac.focusCar(target)
        current_car_id = target
        ac.log("[{}] Focused car (proximity) {}".format(APP_NAME, target))
        return True
    except Exception as ex:
        ac.log("[{}] focusCar failed: {}".format(APP_NAME, ex))
        return False


def update_ui():
    """Refresh labels and button text."""
    now = time.time()
    remaining = next_switch_time - now
    if remaining < 0.0:
        remaining = 0.0

    if status_label is not None:
        ac.setText(status_label, "{} | next: {:0.1f}s".format("running" if enabled else "paused", remaining))

    if camera_label is not None:
        ac.setText(camera_label, "Camera: TV/manual (set with F2/F5/F6) | Mode: Proximity")

    if toggle_button is not None:
        ac.setText(toggle_button, "Pause" if enabled else "Resume")


def toggle_callback(*args):
    """Pause/Resume button callback."""
    global enabled
    enabled = not enabled
    ac.log("[{}] Button pressed. Now: {}".format(APP_NAME, "enabled" if enabled else "paused"))
    if enabled:
        schedule_next_switch()
    update_ui()


# ---------- AC entry points ----------
def acMain(ac_version):
    global app_window, status_label, camera_label, toggle_button

    ac.log("[{}] acMain called".format(APP_NAME))

    app_window = ac.newApp(APP_NAME)
    ac.setTitle(app_window, APP_NAME)
    ac.setSize(app_window, 340, 130)

    status_label = ac.addLabel(app_window, "starting…")
    ac.setPosition(status_label, 10, 30)

    toggle_button = ac.addButton(app_window, "Pause")
    ac.setPosition(toggle_button, 10, 55)
    ac.setSize(toggle_button, 120, 25)
    ac.addOnClickedListener(toggle_button, toggle_callback)

    camera_label = ac.addLabel(app_window, "Camera: TV/manual (set with F2/F5/F6) | Mode: Proximity")
    ac.setPosition(camera_label, 10, 85)

    schedule_next_switch()
    update_ui()

    return APP_NAME


def acUpdate(deltaT):
    global next_switch_time
    now = time.time()

    # Only act when enabled
    if enabled and now >= next_switch_time:
        switched = focus_best_by_proximity()
        # regardless of result, schedule next normal interval
        schedule_next_switch(now)

    update_ui()