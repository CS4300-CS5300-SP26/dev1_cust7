from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
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


def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
        else:
            # Print form errors for debugging
            print(f"Form errors: {form.errors}")
    else:
        form = UserCreationForm()
    return render(request, 'home/register.html', {'form': form})


def signin(request):
    """Simple login view"""
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            error_message = "Invalid username or password"
            return render(request, 'home/signin.html', {'error_message': error_message})
    return render(request, 'home/signin.html')
def signout(request):
    logout(request)
    return redirect('index')

def account(request):
    """Display user account information"""
    if not request.user.is_authenticated:
        return redirect('signin')
    
    return render(request, 'home/account_info.html', {'user': request.user})

@login_required
def pantry_view(request):
    """Display the user's pantry page"""
    pantry_items = request.user.pantry_items.all()
    return render(request, 'home/pantry.html', {'pantry_items': pantry_items})


@login_required
@require_POST
def add_ingredient(request):
    """Add a new ingredient to the user's pantry"""
    try:
        data = json.loads(request.body)
        ingredient_name = data.get('ingredient_name', '').strip()
        
        if not ingredient_name:
            return JsonResponse({'error': 'Ingredient name is required'}, status=400)
        
        # Check if ingredient already exists for this user
        if request.user.pantry_items.filter(ingredient_name__iexact=ingredient_name).exists():
            return JsonResponse({'error': 'Ingredient already in pantry'}, status=400)
        
        # Create new pantry item
        pantry_item = request.user.pantry_items.create(ingredient_name=ingredient_name)
        
        return JsonResponse({
            'success': True,
            'ingredient': {
                'id': pantry_item.id,
                'name': pantry_item.ingredient_name,
                'added_date': pantry_item.added_date.strftime('%Y-%m-%d')
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def delete_ingredient(request, ingredient_id):
    """Remove an ingredient from the user's pantry"""
    try:
        pantry_item = get_object_or_404(request.user.pantry_items, id=ingredient_id)
        pantry_item.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_pantry_ingredients(request):
    """API endpoint to get user's pantry ingredients"""
    pantry_items = request.user.pantry_items.values('id', 'ingredient_name', 'added_date')
    return JsonResponse({
        'ingredients': list(pantry_items)
    })


@login_required
@require_GET
def search_recipes_by_pantry(request):
    """Search for recipes based on pantry ingredients using Spoonacular API"""
    pantry_items = request.user.pantry_items.values_list('ingredient_name', flat=True)
    
    if not pantry_items:
        return JsonResponse({'recipes': [], 'message': 'No ingredients in pantry'})
    
    # Join ingredients with commas for Spoonacular API
    ingredients = ','.join(pantry_items)
    
    # Search for recipes using ingredients
    search_params = urllib.parse.urlencode({
        "ingredients": ingredients,
        "number": 10,  # Get top 10 matching recipes
        "ranking": 1,  # Rank by most matched ingredients
        "ignorePantry": False,
        "apiKey": settings.SPOONACULAR_API_KEY,
    })
    
    #Spoonacular blocks urllib's default user agent
    #Fake regular browser
    req = urllib.request.Request(
        f"https://api.spoonacular.com/recipes/findByIngredients?{search_params}",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    
    try:
        with urllib.request.urlopen(req) as res:
            recipes_data = json.loads(res.read().decode())
        
        # Process recipes to add match counts
        processed_recipes = []
        for recipe in recipes_data:
            used_ingredients = recipe.get('usedIngredients', [])
            missed_ingredients = recipe.get('missedIngredients', [])
            
            processed_recipes.append({
                'id': recipe.get('id'),
                'title': recipe.get('title'),
                'image': recipe.get('image'),
                'used_ingredient_count': len(used_ingredients),
                'missed_ingredient_count': len(missed_ingredients),
                'used_ingredients': [ing['name'] for ing in used_ingredients],
                'missed_ingredients': [ing['name'] for ing in missed_ingredients],
                'missed_ingredients_string': ', '.join([ing['name'] for ing in missed_ingredients])
            })
        
        # Sort by most used ingredients (best matches first)
        processed_recipes.sort(key=lambda x: x['used_ingredient_count'], reverse=True)
        
        return JsonResponse({
            'recipes': processed_recipes,
            'pantry_ingredients': list(pantry_items),
            'api_status': 'success'
        })
        
    except urllib.error.HTTPError as e:
        if e.code == 402:
            # Handle payment required error gracefully
            return JsonResponse({
                'recipes': get_fallback_recipes(pantry_items),
                'pantry_ingredients': list(pantry_items),
                'api_status': 'payment_required',
                'message': 'Recipe API temporarily unavailable. Showing suggested recipes based on your ingredients.',
                'note': 'This feature requires API credits. Please check back later or try adding more ingredients.'
            })
        else:
            return JsonResponse({'error': f"Recipe search failed with HTTP {e.code}: {str(e)}"}, status=502)
    except Exception as e:
        return JsonResponse({'error': f"Recipe search failed: {str(e)}"}, status=502)


def get_fallback_recipes(pantry_items):
    """Generate fallback recipes when API is unavailable"""
    pantry_list = list(pantry_items)
    fallback_recipes = []
    
    # Common recipe templates based on common ingredients
    recipe_templates = [
        {
            'title': 'Simple Stir Fry',
            'base_ingredients': ['chicken', 'beef', 'tofu'],
            'common_ingredients': ['rice', 'vegetables', 'soy sauce'],
            'image': 'https://via.placeholder.com/150x100?text=Stir+Fry'
        },
        {
            'title': 'Pasta with Sauce',
            'base_ingredients': ['pasta', 'spaghetti'],
            'common_ingredients': ['tomato', 'cheese', 'meat'],
            'image': 'https://via.placeholder.com/150x100?text=Pasta'
        },
        {
            'title': 'Omelette',
            'base_ingredients': ['eggs'],
            'common_ingredients': ['cheese', 'vegetables', 'meat'],
            'image': 'https://via.placeholder.com/150x100?text=Omelette'
        },
        {
            'title': 'Soup',
            'base_ingredients': ['chicken', 'beef', 'vegetables'],
            'common_ingredients': ['broth', 'potatoes', 'carrots'],
            'image': 'https://via.placeholder.com/150x100?text=Soup'
        },
        {
            'title': 'Salad',
            'base_ingredients': ['lettuce', 'vegetables'],
            'common_ingredients': ['tomato', 'cheese', 'dressing'],
            'image': 'https://via.placeholder.com/150x100?text=Salad'
        }
    ]
    
    # Match recipes to available ingredients
    for template in recipe_templates:
        # Check if we have at least one base ingredient
        has_base = any(ing.lower() in [p.lower() for p in pantry_list] for ing in template['base_ingredients'])
        # Check if we have at least one common ingredient
        has_common = any(ing.lower() in [p.lower() for p in pantry_list] for ing in template['common_ingredients'])
        
        if has_base or has_common:
            # Count matching ingredients
            matching_ingredients = []
            for ing in template['base_ingredients'] + template['common_ingredients']:
                if ing.lower() in [p.lower() for p in pantry_list]:
                    matching_ingredients.append(ing)
            
            fallback_recipes.append({
                'id': f"fallback_{len(fallback_recipes) + 1}",
                'title': template['title'],
                'image': template['image'],
                'used_ingredient_count': len(matching_ingredients),
                'missed_ingredient_count': max(0, 3 - len(matching_ingredients)),  # Assume 3 total needed
                'used_ingredients': matching_ingredients,
                'missed_ingredients': ['Additional ingredients needed'] if len(matching_ingredients) < 3 else [],
                'missed_ingredients_string': 'Additional ingredients needed' if len(matching_ingredients) < 3 else 'All ingredients available!'
            })
    
    # If no matches, provide generic suggestions
    if not fallback_recipes:
        fallback_recipes = [
            {
                'id': 'fallback_generic_1',
                'title': 'Basic Recipe Suggestions',
                'image': 'https://via.placeholder.com/150x100?text=Recipe',
                'used_ingredient_count': 0,
                'missed_ingredient_count': 3,
                'used_ingredients': [],
                'missed_ingredients': ['Try adding common ingredients like chicken, rice, or vegetables'],
                'missed_ingredients_string': 'Add more ingredients for better recipe matches'
            }
        ]
    
    # Sort by ingredient matches
    fallback_recipes.sort(key=lambda x: x['used_ingredient_count'], reverse=True)
    
    return fallback_recipes[:5]  # Return top 5 suggestions
