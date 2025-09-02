# Changelog

## Unreleased (pushed to `main`)

Highlights
- Collision detection: now requires nearby rival, minimum real time window, and 2-tick confirmation with cooldown to eliminate heavy-braking false positives. Yaw only increases severity; it is no longer sufficient to trigger by itself.
- Offtrack detection: adds drop ratio bounds, average yaw confirmation, and a short confirmation window with cooldown to cut noise.
- Smarter focus: prevents focusing near-stationary cars on events; auto-focuses the leader at app start and once during start lights.
- Shot timing: longer dwell when race intensity is low and up to 20% shorter shots at high intensity.
- UI: simplified; removed camera/mode/status labels, added focus info (car id + reason).
- Force TV: uses F3 via ctypes; logs import failure details if ctypes is unavailable.

Technical details
- detectors.py
  - Build spatial grid each scan and require nearest rival within `COLLISION_NEAR_RADIUS_M` for collisions.
  - Enforce `COLLISION_MIN_DT_S` and confirmation window `COLLISION_CONFIRM_WINDOW_S` using a per-car pending map.
  - Offtrack requires sustained conditions: drop, ratio, yaw instant + average, and confirmation window; cooldowns for both events.
- config.py
  - Added tunables: collision/offtrack thresholds, ratios, min dt, confirmation windows, cooldowns.
  - Filtering: `IGNORE_STOPPED_CARS`, `STOPPED_SPEED_KMH`, `MIN_FOCUS_SPEED_KMH` to ignore stationary cars and avoid focusing them.
  - Dwell shaping: `LOW_INTENSITY_BONUS`, `HIGH_INTENSITY_SHORTEN_MAX`.
- scheduler.py
  - `_natural_interval()` scales with race intensity: longer at low intensity, up to 20% shorter at high intensity.
- app.py
  - Focus leader at startup and during start lights phase (once) based on spline ranking.
  - Removed camera/mode/status labels creation; Force TV button listener attached only if ctypes available.
- ui.py
  - `force_tv_cam` sends F3 via ctypes; logs ctypes import failure (`[APP] ctypes import failed: ...`).
  - Shows current focus id and reason.
- state.py / focus.py
  - Track current reason for display; block focusing near-stationary on events.

Configuration tips
- If collisions are still too sensitive, raise `COLLISION_MIN_DECEL_KMH_S` (e.g., 180) or `COLLISION_MIN_DROP_RATIO` (e.g., 0.35), or increase `COLLISION_MIN_DT_S` to 0.20.
- If offtracks miss some cases, lower `OFFTRACK_MIN_DROP_RATIO` (e.g., 0.20) and/or widen `OFFTRACK_CONFIRM_WINDOW_S` to 0.4.

