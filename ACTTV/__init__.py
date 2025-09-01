# This package marker file allows Assetto Corsa to recognize the app
# directory as a Python package. It can be empty.

# Expose the entry points for Assetto Corsa.
# Assetto Corsa imports this package by its directory name, so the actual
# implementation lives in ``app.py`` and we re-export the required functions
# here for clarity and compatibility with Python 3.3.
from .app import acMain, acUpdate
