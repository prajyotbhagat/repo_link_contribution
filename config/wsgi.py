import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django
application = get_wsgi_application()

# Run the seeding script right after initialization
try:
    from .initializer import create_initial_superuser
    create_initial_superuser()
except Exception as e:
    print(f"Initialization failed: {e}")
