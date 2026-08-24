"""
ASGI config for Property Business AI.

Exposes the ASGI callable as a module-level variable named ``application``.
Included for future use (e.g. WebSocket support for real-time notifications).
V1 uses standard WSGI; this file is not active in Phase 1.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_asgi_application()
