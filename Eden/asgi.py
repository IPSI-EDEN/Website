"""
ASGI config for Eden project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
import django
from channels.routing import ProtocolTypeRouter, get_default_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Eden.settings')
django.setup()
from .routing import application