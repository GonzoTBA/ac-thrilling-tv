# Package marker and re-exports for Assetto Corsa.
try:
    from .app import acMain, acUpdate  # re-export entry points
except Exception:
    # In case of partial import during editor/runtime probing
    def acMain(ac_version):
        return "ACTTV"

    def acUpdate(deltaT):
        return
