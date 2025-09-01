"""Camera focusing logic based on car proximity."""

import ac
import acsys

from . import config, state


def get_world_pos(car_id):
    """Return (x, y, z) world position or None on error."""
    try:
        return ac.getCarState(car_id, acsys.CS.WorldPosition)
    except Exception:
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
    except Exception:
        return False


def pick_best_car_by_proximity():
    """Return the car_id with the most nearby rivals."""
    car_count = ac.getCarsCount()
    if car_count < config.MIN_CARS_REQUIRED:
        return None

    positions = [get_world_pos(i) for i in range(car_count)]
    actives = [is_car_active(i) and (positions[i] is not None) for i in range(car_count)]

    best_car = None
    best_score = -1.0
    near_r2 = config.NEAR_RADIUS_M * config.NEAR_RADIUS_M

    for i in range(car_count):
        if not actives[i]:
            continue
        pi = positions[i]
        score = 0.0

        for j in range(car_count):
            if i == j or not actives[j]:
                continue
            pj = positions[j]
            d2 = distance_sq(pi, pj)
            if d2 <= near_r2:
                score += 1.0 + (0.5 / (1.0 + d2))

        if score > best_score or (score == best_score and i != state.current_car_id):
            best_score = score
            best_car = i

    if best_car is None:
        for i in range(car_count):
            if actives[i]:
                best_car = i
                break

    return best_car


def focus_best_by_proximity():
    """Focus the car selected by proximity scoring."""
    target = pick_best_car_by_proximity()
    if target is None:
        ac.log("[{}] No suitable target (proximity).".format(config.APP_NAME))
        return False
    try:
        ac.focusCar(target)
        state.current_car_id = target
        ac.log("[{}] Focused car (proximity) {}".format(config.APP_NAME, target))
        return True
    except Exception as ex:
        ac.log("[{}] focusCar failed: {}".format(config.APP_NAME, ex))
        return False

