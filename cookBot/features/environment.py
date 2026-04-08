import os
import django
from django.test import Client

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cookBot.settings")
django.setup()


def before_scenario(context, scenario):
    context.client = Client()
