"""
WSGI config for YuGiOhOnline1 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
import socketio

from socketio_app.views import sio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'YuGiOhOnline1.settings')

static_files = {
        '/static' : 'socketio_app/static', #OH MY GOD WHY
}

#WHY

django_app = get_wsgi_application()
application = socketio.WSGIApp(sio, django_app, static_files=static_files)
