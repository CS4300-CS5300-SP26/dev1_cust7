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
    # Only delete test users (never delete admin accounts or real fixtures)
    User.objects.filter(username__startswith='test_').delete()
    User.objects.filter(username__startswith='bookmark_').delete()
    User.objects.filter(username__startswith='comment_').delete()
    User.objects.filter(username__startswith='other_user').delete()
    
    context.client = Client()
