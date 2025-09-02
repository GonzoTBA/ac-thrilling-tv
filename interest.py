"""Interest scoring and race intensity computation."""

import math
from . import config, state
from . import spatial
from .scheduler import set_race_intensity


_ema_intensity = 0.0
_last_intensity_t = 0.0


def _clamp(x, a, b):
    if x < a:
        return a
    if x > b:
        return b
    return x


def _distance_xz(p1, p2):
    dx = p1[0] - p2[0]
    dz = p1[2] - p2[2]
    return math.sqrt(dx * dx + dz * dz)


def _proximity_score(i, grid):
    pi = state.pos(i)
    if pi is None:
        return 0.0
    R = config.PROX_RADIUS_M
    R2 = R * R
    beta = config.BETA_NEAREST

    nearest_term = 0.0
    sum_extras = 0.0
    k = 0
    for j in spatial.neighbors_of(i, pi, grid):
        pj = state.pos(j)
        if pj is None:
            continue
        dx = pi[0] - pj[0]
        dz = pi[2] - pj[2]
        d2 = dx * dx + dz * dz
        if d2 > R2:
            continue
        d = math.sqrt(d2)
        if nearest_term < 1.0:
            nearest_term = max(nearest_term, 1.0 - (d / R))
        w = 1.0 / (1.0 + (d / R) * (d / R))
        sum_extras += w
        k += 1
        if k >= config.PROX_K:
            break

    if k == 0 and nearest_term == 0.0:
        return 0.0
    return beta * nearest_term + (1.0 - beta) * sum_extras


def _leader_moment(i, n):
    # Approximate field position from spline (front is higher spline)
    # Build order by descending spline
    ranks = sorted([(state.spline(c), c) for c in range(n)], reverse=True)
    pos_index = 0
    for idx in range(n):
        if ranks[idx][1] == i:
            pos_index = idx + 1
            break
    leader_base = float(n - pos_index + 1) / float(n) if n > 0 else 0.0

    progress = state.spline(i)
    start_w = config.LEADER_START_WINDOW
    end_w = config.LEADER_END_WINDOW
    # Envelope: boost at start/finish of race lap
    envelope = 1.0
    if progress <= start_w:
        envelope = progress / start_w if start_w > 0.0 else 1.0
    elif progress >= (1.0 - end_w):
        tail = 1.0 - progress
        envelope = tail / end_w if end_w > 0.0 else 1.0
    return leader_base * envelope


def _rarity(i, now, n):
    last = state.last_focused_at(i)
    dt = now - last if last > 0.0 else 1e9
    rarity_full_after = max(15.0, 0.5 * config.DWELL_BASE * max(1, n))
    return _clamp(dt / rarity_full_after, 0.0, 1.0)


def _hysteresis(i, now):
    last = state.last_focused_at(i)
    if last <= 0.0:
        return 0.0
    return 1.0 if (now - last) < config.HYSTERESIS_WINDOW else 0.0


def _pit_cameo(i):
    # External detector should set a transient flag if desired; default 0
    return 0.0


def _compute_race_intensity(n, grid, now):
    # battle_density from gaps in space (R) ignoring time gaps
    R = config.BATTLE_RADIUS_M
    pairs = 0
    tested = set()
    for i in range(n):
        pi = state.pos(i)
        if pi is None:
            continue
        for j in spatial.neighbors_of(i, pi, grid):
            if j <= i:
                continue
            key = (i, j)
            if key in tested:
                continue
            pj = state.pos(j)
            if pj is None:
                continue
            d = _distance_xz(pi, pj)
            if d < R:
                pairs += 1
            tested.add(key)
    max_pairs_norm = max(1.0, float(n) / 2.0)
    battle_density = _clamp(float(pairs) / max_pairs_norm, 0.0, 1.0)

    # event_activity not tracked precisely; approximate with recent speed drops density
    # Keep 0 for simplicity in MVP; battle dominates with ALPHA_BATTLE
    event_activity = 0.0

    raw = config.ALPHA_BATTLE * battle_density + (1.0 - config.ALPHA_BATTLE) * event_activity

    global _ema_intensity, _last_intensity_t
    if _last_intensity_t == 0.0:
        _ema_intensity = raw
        _last_intensity_t = now
    else:
        dt = now - _last_intensity_t
        _last_intensity_t = now
        # EMA with time constant tau
        tau = max(0.001, config.EMA_TAU)
        a = 1.0 - math.exp(-dt / tau)
        _ema_intensity = (1.0 - a) * _ema_intensity + a * raw
    set_race_intensity(_clamp(_ema_intensity, 0.0, 1.0))


def pick_best_by_interest(st, now):
    n = st.car_count()
    if n < config.MIN_CARS_REQUIRED:
        return -1
    grid = spatial.build_grid(st, config.CELL_SIZE_M)
    _compute_race_intensity(n, grid, now)

    best = -1
    best_score = -9999.0
    unseen = st.unseen_set()

    for c in range(n):
        if not st.active(c):
            continue
        prox = _proximity_score(c, grid)
        leader = _leader_moment(c, n)
        rarity = _rarity(c, now, n)
        hyst = _hysteresis(c, now)
        pit = _pit_cameo(c)

        score = (
            config.W_PROX * prox
            + config.W_LEADER * leader
            + config.W_RARITY * rarity
            - config.W_HYST * hyst
            + config.W_PIT * pit
        )

        if c in unseen:
            score += config.UNSEEN_BONUS

        if score > best_score:
            best_score = score
            best = c

    return best

