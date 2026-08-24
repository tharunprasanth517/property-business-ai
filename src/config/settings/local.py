"""
Local / development settings for Property Business AI.

Extends base.py. Used when DJANGO_SETTINGS_MODULE=config.settings.local.
"""

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Development mode
# ---------------------------------------------------------------------------

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# ---------------------------------------------------------------------------
# Development logging — print SQL queries and errors to the console
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG",  # Set to "INFO" to silence SQL query logs
            "propagate": False,
        },
    },
}
