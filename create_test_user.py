#!/usr/bin/env python3
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, '/home/dx14/Documents/GITHUB/CS-4300/dev1_cust7/cookBot')

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cookBot.settings')

# Setup Django
django.setup()

from django.contrib.auth.models import User

def create_test_user():
    """Create a test user for demonstration"""
    username = 'testuser'
    password = 'testpass123'
    
    if User.objects.filter(username=username).exists():
        print(f"User '{username}' already exists.")
        return User.objects.get(username=username)
    
    user = User.objects.create_user(
        username=username,
        password=password
    )
    print(f"Created test user: {username}")
    print(f"Password: {password}")
    return user

if __name__ == '__main__':
    create_test_user()