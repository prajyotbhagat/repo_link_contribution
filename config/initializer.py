import os
from django.contrib.auth.models import User

def create_initial_superuser():
    # Fetch credentials from Vercel Environment Variables
    username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "YourSecurePassword123")

    # Only create if the user table is empty or user doesn't exist
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f"Superuser '{username}' created successfully.")
