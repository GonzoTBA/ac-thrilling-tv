import ac
import random
import time

APP_NAME = "ACTTV"

# Config
BASE_INTERVAL = 10.0
JITTER = 3.0
MIN_CARS_REQUIRED = 1

# UI / State
app_window = None
status_label = None
camera_label = None
toggle_button = None

next_switch_time = 0.0
current_car_id = -1
enabled = True


def schedule_next_switch(now=None):
    """Schedule next switch (respects jitter)."""
    global next_switch_time
    if now is None:
        now = time.time()
    interval = BASE_INTERVAL + random.uniform(-JITTER, JITTER)
    if interval < 3.0:
        interval = 3.0
    next_switch_time = now + interval
    ac.log("[{}] Next switch scheduled in {:.1f}s".format(APP_NAME, interval))


def focus_random_car():
    """Focus a random car; keeps whatever camera mode the user set (F2/F5/F6)."""
    global current_car_id
    car_count = ac.getCarsCount()
    if car_count < MIN_CARS_REQUIRED:
        ac.log("[{}] Not enough cars ({}).".format(APP_NAME, car_count))
        return False

    target_car_id = random.randint(0, max(0, car_count - 1))
    if car_count > 1 and target_car_id == current_car_id:
        target_car_id = (target_car_id + 1) % car_count

    try:
        ac.focusCar(target_car_id)
        current_car_id = target_car_id
        ac.log("[{}] Focused car {}".format(APP_NAME, target_car_id))
        return True
    except Exception as ex:
        ac.log("[{}] focusCar failed for {}: {}".format(APP_NAME, target_car_id, ex))
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
        # Informational only: AC Python API cannot read/set exact TV cam (use F2/F5/F6 manually)
        ac.setText(camera_label, "Camera: TV/manual (set with F2/F5/F6)")
    if toggle_button is not None:
        ac.setText(toggle_button, "Pause" if enabled else "Resume")


def toggle_callback(*args):
    """Start/Stop button callback (signature tolerant)."""
    global enabled
    enabled = not enabled
    ac.log("[{}] Button pressed. Now: {}".format(APP_NAME, "enabled" if enabled else "paused"))
    if enabled:
        schedule_next_switch()
    update_ui()


def acMain(ac_version):
    global app_window, status_label, camera_label, toggle_button

    ac.log("[{}] acMain called".format(APP_NAME))

    app_window = ac.newApp(APP_NAME)
    ac.setTitle(app_window, APP_NAME)
    ac.setSize(app_window, 320, 130)

    status_label = ac.addLabel(app_window, "starting…")
    ac.setPosition(status_label, 10, 30)

    toggle_button = ac.addButton(app_window, "Pause")
    ac.setPosition(toggle_button, 10, 55)
    ac.setSize(toggle_button, 120, 25)
    ac.addOnClickedListener(toggle_button, toggle_callback)

    camera_label = ac.addLabel(app_window, "Camera: TV/manual (set with F2/F5/F6)")
    ac.setPosition(camera_label, 10, 85)

    schedule_next_switch()
    update_ui()

    return APP_NAME


def acUpdate(deltaT):
    global next_switch_time
    now = time.time()

    # Respect pause strictly
    if enabled and now >= next_switch_time:
        switched = focus_random_car()
        # Regardless of result, schedule next normal interval (no spam)
        schedule_next_switch(now)

    update_ui()