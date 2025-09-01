# AutoDirector - MVP random camera switcher
# Place this file in ...\Assetto Corsa\apps\python\AutoDirector\app.py

import ac
import acsys
import random
import time

APP_NAME = "AutoDirector"

# Configuration
BASE_INTERVAL = 10.0         # base time in seconds between camera switches
JITTER = 3.0                 # random +/- time in seconds
MIN_CARS_REQUIRED = 1        # minimum cars required to perform a switch

# Global state
app_window = None
status_label = None
next_switch_time = 0.0
current_car_id = -1
enabled = True


def schedule_next_switch(now=None):
    """Schedule the next camera switch with random jitter."""
    global next_switch_time
    if now is None:
        now = time.time()
    interval = BASE_INTERVAL + random.uniform(-JITTER, JITTER)
    interval = max(3.0, interval)  # never less than 3 seconds
    next_switch_time = now + interval


def set_camera_mode_safe():
    """Try to set a safe camera mode (some builds may not support this)."""
    try:
        # Options include: acsys.CM_Follow, acsys.CM_Fixed,
        # acsys.CM_Free, acsys.CM_DriverEye, acsys.CM_Cockpit
        ac.setCameraMode(acsys.CM_Fixed)
    except Exception:
        pass


def focus_random_car():
    """Switch focus to a random car."""
    global current_car_id
    car_count = ac.getCarsCount()
    if car_count < MIN_CARS_REQUIRED:
        return False

    # Choose a random car (0..car_count-1). Avoid repeating the same if possible.
    target_car_id = random.randint(0, max(0, car_count - 1))
    if car_count > 1 and target_car_id == current_car_id:
        target_car_id = (target_car_id + 1) % car_count

    try:
        ac.focusCar(target_car_id)
        current_car_id = target_car_id
        return True
    except Exception:
        # If focusing fails, just ignore for this MVP
        return False


def update_status_label():
    """Update the small UI label showing current state."""
    if status_label is None:
        return
    now = time.time()
    remaining = max(0.0, next_switch_time - now)
    text = "running" if enabled else "paused"
    ac.setText(status_label, f"{text} | next: {remaining:0.1f}s")


def acMain(ac_version):
    """Main entry point called by Assetto Corsa."""
    global app_window, status_label

    app_window = ac.newApp(APP_NAME)
    ac.setSize(app_window, 230, 60)
    ac.drawBorder(app_window, 1)
    ac.setTitle(app_window, APP_NAME)

    status_label = ac.addLabel(app_window, "starting…")
    ac.setPosition(status_label, 10, 30)

    # Try to set camera mode
    set_camera_mode_safe()

    # Schedule the first switch
    schedule_next_switch()

    return APP_NAME


def acUpdate(deltaT):
    """Update loop called by Assetto Corsa each frame."""
    global enabled

    now = time.time()

    # Perform switch if it's time
    if enabled and now >= next_switch_time:
        if focus_random_car():
            schedule_next_switch(now)
        else:
            # If no cars available, retry soon
            schedule_next_switch(now + 2.0)

    update_status_label()