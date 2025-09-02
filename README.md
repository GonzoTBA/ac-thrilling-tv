# ACT Thrilling TV (ACTTV)

An Assetto Corsa in‑game Python app that automatically switches camera focus to the most interesting car on track. It blends “natural” camera cuts (based on proximity and race context) with event‑driven interrupts (e.g., collisions, off‑tracks, pit entry), while adapting shot duration to the current race intensity.

## What It Does
- Automatically focuses the most compelling on‑track action.
- Interrupts natural cuts for significant events like collisions or off‑tracks.
- Extends or shortens dwell time based on race intensity (longer when calm, up to 20% shorter when hectic).
- Avoids focusing stationary cars and shows a small status line with current focus and reason.

## High‑Level Focus Algorithm

ACTTV runs at each game tick and follows two lanes of logic: natural focus selection and event interrupts. A simple scheduler governs when natural cuts happen; event interrupts can preempt them.

- Natural Focus Selection (scored pick)
  - Build a spatial grid and compute a score per car using:
    - Proximity: favors cars near rivals within a radius, mixing nearest distance and a capped sum of nearby opponents.
    - Leader Moment: boosts leaders slightly, modulated by lap progress (start/finish sensitivity).
    - Rarity: prefers cars not shown recently; grows with time since last focus.
    - Hysteresis: applies a small negative bias to the current/very‑recent focus to avoid choppy flips.
    - Pit Cameo: small optional boost when a pit‑related moment is detected.
  - Combine terms with tunable weights; pick the car with the highest score.

- Event Interrupts (preemptive)
  - Collisions: require a real deceleration over a minimum time window AND a nearby rival within a short range. A short confirmation window (two consecutive ticks) and a per‑car cooldown reduce noise. Yaw (spin tendency) increases severity but is not required by itself.
  - Off‑Tracks: require a significant speed drop with plausible current speed, yaw within a moderate range, and an average yaw confirmation; also uses a brief confirmation window and cooldown.
  - Pit Entry: simple heuristic based on pitlane flags and low speed.
  - Events are prioritized (collision > spin > offtrack > pit_entry) and may temporarily lock the camera (event dwell) before natural switching resumes.

- Scheduler and Race Intensity
  - Race intensity is an EMA derived from opponent density within a battle radius. It drives dwell time:
    - Longer shots at low intensity (configurable bonus).
    - Up to 20% shorter shots at high intensity (configurable cap).
  - A jitter is added to avoid robotic timing.

- Guards and Filters
  - Ignores cars at or below a small stopped speed threshold for detectors.
  - Avoids switching to near‑stationary cars on event interrupts.
  - Applies event dwell locks (short camera “hold” after interrupts).

## Configuration
All tunables live in `config.py`.

Key groups:
- Filtering: `IGNORE_STOPPED_CARS`, `STOPPED_SPEED_KMH`, `MIN_FOCUS_SPEED_KMH`.
- Collision thresholds: `COLLISION_WINDOW_S`, `COLLISION_MIN_DT_S`, `COLLISION_MIN_DROP_KMH`, `COLLISION_MIN_PRE_SPEED_KMH`, `COLLISION_MIN_DROP_RATIO`, `COLLISION_MIN_DECEL_KMH_S`, `COLLISION_MAX_POST_SPEED_KMH`, `COLLISION_NEAR_RADIUS_M`, `COLLISION_CONFIRM_WINDOW_S`, `COLLISION_COOLDOWN_S`.
- Offtrack thresholds: `OFFTRACK_WINDOW_S`, `OFFTRACK_MIN_DROP_KMH`, `OFFTRACK_MIN_PRE_SPEED_KMH`, `OFFTRACK_MIN_NOW_SPEED_KMH`, `OFFTRACK_MAX_NOW_SPEED_KMH`, `OFFTRACK_MIN_DROP_RATIO`, `OFFTRACK_MAX_DROP_RATIO`, `OFFTRACK_YAW_MIN_RAD_S`, `OFFTRACK_AVG_YAW_MIN_RAD_S`, `OFFTRACK_CONFIRM_WINDOW_S`, `OFFTRACK_COOLDOWN_S`.
- Scoring weights: `W_PROX`, `W_LEADER`, `W_RARITY`, `W_HYST`, `W_PIT`.
- Dwell and intensity shaping: `DWELL_BASE`, `JITTER_RANGE`, `K_INTENSITY`, `LOW_INTENSITY_BONUS`, `HIGH_INTENSITY_SHORTEN_MAX`.
- Performance: `CELL_SIZE_M`, `PROX_K`, `MAX_DISTANCE_TESTS_PER_SEC`.

## UI
- Status label: shows app state, time to next cut, and current race intensity.
- Focus label: displays the current car id and reason (natural or event type).
- Force TV button: sends F3 via Windows `ctypes` (if available). If `ctypes` cannot be imported in the embedded Python, the button is disabled and the import error is logged for diagnosis.

## Installation (brief)
- Copy the project folder into your Assetto Corsa apps/python directory.
- Enable the app in Assetto Corsa’s settings. Start a session and toggle the app window.
- Optional: adjust `config.py` to fit your preferences and track/car combo.

## Tuning Tips
- If collisions are still too sensitive, increase `COLLISION_MIN_DECEL_KMH_S` or `COLLISION_MIN_DROP_RATIO`, or raise `COLLISION_MIN_DT_S` slightly.
- If off‑tracks are missed, lower `OFFTRACK_MIN_DROP_RATIO` or increase `OFFTRACK_CONFIRM_WINDOW_S`.
- To hold shots longer, raise `DWELL_BASE` or `LOW_INTENSITY_BONUS`; to be snappier in action, increase `HIGH_INTENSITY_SHORTEN_MAX` moderately.

## Limitations
- The app relies on the quality of speed, velocity, and pitlane signals exposed by Assetto Corsa. Edge cases (very low FPS or unusual mods) can affect detectors.
- The “leader” at session start is estimated via normalized spline ranking.
- Force TV requires `ctypes` in AC’s embedded Python. If the module is not present or cannot load due to missing system runtimes, the button is disabled.

## Contributing
Issues and PRs are welcome. If you tweak thresholds for a specific league/car class, consider sharing your settings and rationale so others can benefit.

