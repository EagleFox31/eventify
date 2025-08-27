"""
WSGI config for eventify project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventify.settings')

# --- Auto-migrate on startup ---
try:
    from django.core.management import call_command
    call_command("migrate", interactive=False, run_syncdb=True)
    call_command("collectstatic", interactive=False, verbosity=0, clear=True, link=True)
except Exception as e:
    # On logge l'erreur pour Render mais on ne bloque pas l'app
    sys.stderr.write(f"⚠️ Erreur pendant migrate/collectstatic: {e}\n")

# --- Lancer l'application ---
application = get_wsgi_application()
