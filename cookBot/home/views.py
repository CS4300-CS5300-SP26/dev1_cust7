from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from collections import defaultdict
from django.http import JsonResponse
from django.conf import settings
import json
import urllib.request
import urllib.parse


def index(request):
    return render(request, 'index.html')

####Help from Claude and Spoonacular documents on fetching data from spoonacular####
def get_nutrition(request, ingredient_name):
    #API key from settings.py
    api_key = settings.SPOONACULAR_API_KEY

    #Search for ingredient ID from spoonacular
    search_params = urllib.parse.urlencode({
        "query": ingredient_name,
        "apiKey": api_key,
        "number": 1,
    })
    
    #Spoonacular blocks urllib's default user agent
    #Fake regular browser
    req = urllib.request.Request(
        f"https://api.spoonacular.com/food/ingredients/search?{search_params}",
        headers={"User-Agent": "Mozilla/5.0"}  
    )
    try:
        with urllib.request.urlopen(req) as res:
            search_data = json.loads(res.read().decode())
    except Exception as e:
        print(f"SEARCH ERROR: {type(e).__name__}: {e}")
        return JsonResponse({"error": f"Search request failed: {str(e)}"}, status=502)

    results = search_data.get("results", [])
    if not results:
        return JsonResponse(
            {"error": f"No ingredient found matching '{ingredient_name}'"},
            status=404,
        )
    #ingredient ID
    ingredient_id = results[0]["id"]
    

    #Fetch full nutrition information based on ingredient ID
    nutrition_params = urllib.parse.urlencode({
        "amount": 1,
        "apiKey": api_key,
    })

    #Spoonacular blocks urllib's default user agent
    #Fake regular browser
    nutrition_req = urllib.request.Request(
        f"https://api.spoonacular.com/food/ingredients/{ingredient_id}/information?{nutrition_params}",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(nutrition_req) as res:
            nutrition_data = json.loads(res.read().decode())
    except Exception as e:
        return JsonResponse({"error": f"Nutrition request failed: {str(e)}"}, status=502)

    return JsonResponse(nutrition_data)
####End spoonacular API call function####

def nutrition_test(request):
    return render(request, 'home/nutrition_test.html')
