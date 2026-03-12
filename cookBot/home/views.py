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
import re

def index(request):
    return render(request, 'index.html')

####Help from Claude and Spoonacular documents on fetching data from spoonacular####
def get_nutrition(request, ingredient_name):

    #Search for ingredient ID from spoonacular
    try:
        search_res = requests.get(
            "https://api.spoonacular.com/food/ingredients/search",
            params={
                "query": ingredient_name,
                "apiKey": api_key,
                "number": 1,           # only need the top result
                "metaInformation": True,
            },
            timeout = 10,
        )
        search_res.raise_for_status()
    except requests.RequestException as e:
        return return JsonResponse({"error": f"Search request failed: {str(e)}"}, status=502)

    results = search_res.json().get("results", [])

    #Error if ingredient not found in spoonacular
    if not results:
        return JsonResponse(
            {"error": f"No ingredient found matching '{ingredient_name}'"},
            status=404,
        )

    #Ingredient ID
    ingredient_id = results[0]["id"]
    

    #Fetch full nutrition information based on ingredient ID
    try:
        nutrition_res = requests.get(
            f"https://api.spoonacular.com/food/ingredients/{ingredient_id}/information",
            params={
                "amount": 1,
                "apiKey": api_key,
                "nutrientValues": True,   # includes caloricBreakdown + weightPerServing
            },
            timeout=10,
        )
        nutrition_res.raise_for_status()
    except requests.RequestException as e:
        return JsonResponse({"error": f"Nutrition request failed: {str(e)}"}, status=502)

    #Return nutrition information from spoonacular
    return JsonResponse(nutrition_res.json())
####End spoonacular API call function####