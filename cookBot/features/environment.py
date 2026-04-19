import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cookBot.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from home.models import Recipe, Comment

def before_scenario(context, scenario):
    # Clean database before every test run
    Comment.objects.all().delete()
    Recipe.objects.all().delete()
    User.objects.all().delete()
    
    context.client = Client()
