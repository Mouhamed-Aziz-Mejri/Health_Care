import os
import sys

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

# ASGI application
from django.core.asgi import get_asgi_application

app = get_asgi_application()
