#!/usr/bin/env python3
import os
import sys
import django
from pathlib import Path

# Add the project directory to the Python path
base_dir = Path(__file__).resolve().parent / "cookBot"
sys.path.insert(0, str(base_dir))

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cookBot.settings")

# Setup Django
django.setup()

from django.contrib.auth.models import User


def create_test_user():
    """Create a test user for demonstration"""
    username = "testuser"
    password = "testpass123"

    if User.objects.filter(username=username).exists():
        print(f"User '{username}' already exists.")
        return User.objects.get(username=username)

    user = User.objects.create_user(username=username, password=password)
    print(f"Created test user: {username}")
    print(f"Password: {password}")
    return user


if __name__ == "__main__":
    create_test_user()
