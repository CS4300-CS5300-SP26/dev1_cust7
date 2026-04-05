from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.conf import settings
from .spoonacular import spoonacular_get
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from .models import Recipe, RecipeStep, RecipeIngredient
import json
import urllib.request
import urllib.parse


def index(request):
    return render(request, 'index.html')

####Help from Claude and Spoonacular documents on fetching data from spoonacular####
def get_nutrition(request, ingredient_name):
    try:
        # Step 1: find ingredient ID
        search_data = spoonacular_get("food/ingredients/search", {
            "query": ingredient_name,
            "number": 1,
        })
    except Exception as e:
        return JsonResponse({"error": f"Search request failed: {str(e)}"}, status=502)

    results = search_data.get("results", [])
    if not results:
        return JsonResponse(
            {"error": f"No ingredient found matching '{ingredient_name}'"},
            status=404,
        )

    ingredient_id = results[0]["id"]

    try:
        # Step 2: fetch nutrition by ID
        nutrition_data = spoonacular_get(f"food/ingredients/{ingredient_id}/information", {
            "amount": 1,
        })
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
    try:
        recipes_data = spoonacular_get("recipes/findByIngredients", {
            "ingredients": ingredients,
            "number": 10,
            "ranking": 1,
            "ignorePantry": False,
        })
        
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

# This is for the Recipe viewing page and Recipe Input page
def recipe_view(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)

    # If the recipe is not public, only the owner can view it
    if not recipe.is_public:
        if not request.user.is_authenticated or request.user != recipe.user:
            raise PermissionDenied

    steps = list(recipe.steps.order_by('order').values_list('text', flat=True))

    ingredients = [
        " ".join(
            part for part in (
                (i.quantity or "").strip(),
                (i.unit or "").strip(),
                (i.name or "").strip(),
            ) if part
    )
    for i in recipe.ingredients.all()
]

    return render(request, "recipe_view.html", {
        "recipe": recipe,
        "steps_json": steps,
        "ingredients_json": ingredients,
    })

@login_required
def create_recipe(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        is_public = request.POST.get("is_public") == "on"

        # Server-side validation
        if not title:
            return render(request, "create_recipe.html", {
                "error": "Title cannot be empty.",
                "post_data": request.POST,
            })

        # Create recipe
        recipe = Recipe.objects.create(
            user=request.user,
            title=title,
            is_public=is_public
        )

        # Get ingredient data
        quantities = request.POST.getlist('ingredient_quantity[]')
        units = request.POST.getlist('ingredient_unit[]')
        names = request.POST.getlist('ingredient_name[]')

        for qty, unit, name in zip(quantities, units, names):
            if name.strip():
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    quantity=qty,
                    unit=unit,
                    name=name.strip()
                )

        # Get step data
        steps = request.POST.getlist('steps[]')
        for i, step_text in enumerate(steps, start=1):
            if step_text.strip():
                RecipeStep.objects.create(
                    recipe=recipe,
                    order=i,
                    text=step_text.strip()
                )

        return redirect("recipe_view", recipe_id=recipe.id)

    return render(request, "create_recipe.html")

#Social feed view
@login_required
def social_feed(request):
    """Display a feed of all public recipes from all users, newest first"""
    public_recipes = Recipe.objects.filter(is_public=True).order_by('-created_date')
    return render(request, 'home/social_feed.html', {'public_recipes': public_recipes})
 