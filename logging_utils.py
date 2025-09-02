"""Small helpers to keep logs consistent in AC."""

import ac

PREFIX = "[ACTTV] "


def log(msg):
    try:
        ac.log(PREFIX + str(msg))
    except Exception:
        pass

