from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.conf import settings
from .spoonacular import spoonacular_get
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from .models import Recipe, RecipeStep, RecipeIngredient, ChatSession, ChatMessage
import json
import urllib.request
import urllib.parse
from .forms import RegisterForm, EditProfileForm
from .chefBot import call_openai
from PIL import Image


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
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
        # Form is invalid - render with errors
        return render(request, 'home/register.html', {'form': form})
    else:
        form = RegisterForm()

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
def account(request):
    return render(request, 'home/account_info.html', {'user': request.user})

@login_required
def edit_account(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('account')
    else:
        form = EditProfileForm(instance=request.user)

    return render(request, 'home/edit_account.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('account')

    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'home/change_password.html', {'form': form})

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

@login_required
@require_GET
def get_meals_json(request):
    """API endpoint to get user's meal plans for FullCalendar.io"""
    from .models import MealPlan
    from datetime import datetime, timedelta
    
    # Get optional date range parameters from query string
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Default to current month if not provided
    if not start_date or not end_date:
        today = datetime.now()
        start_date = today.replace(day=1).strftime('%Y-%m-%d')
        # End of current month
        if today.month == 12:
            end_of_month = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month+1, day=1) - timedelta(days=1)
        end_date = end_of_month.strftime('%Y-%m-%d')
    
    # Query only the current user's meal plans within date range
    meals = MealPlan.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Format for FullCalendar.io
    calendar_events = []
    for meal in meals:
        calendar_events.append({
            'id': meal.id,
            'title': meal.recipe_name,
            'start': meal.date.isoformat(),
            'meal_type': meal.meal_type,
            'recipe_id': meal.recipe_id,
        })
    
    return JsonResponse({'meals': calendar_events})


@login_required
def calendar_view(request):
    """Render the meal calendar page"""
    return render(request, 'home/calendar.html')


@login_required
@require_POST
def generate_meal_plan(request):
    """Generate a 7-day meal plan based on user's pantry ingredients"""
    from .models import MealPlan
    from datetime import timedelta, date
    
    # Get user's pantry ingredients
    pantry_items = list(request.user.pantry_items.values_list('ingredient_name', flat=True))
    
    if not pantry_items:
        return JsonResponse({
            'error': 'Your pantry is empty! Add some ingredients to generate a meal plan.'
        }, status=400)
    
    # Join ingredients for Spoonacular API
    ingredients = ','.join(pantry_items)
    
    # Fetch 7 recipes from Spoonacular based on pantry ingredients
    recipes_data = None
    try:
        recipes_data = spoonacular_get("recipes/findByIngredients", {
            "ingredients": ingredients,
            "number": 7,
            "ranking": 1,
            "ignorePantry": False,
        })
    except Exception:
        # If API call fails, use fallback recipes
        pass
    
    if not recipes_data:
        # Fallback to suggested recipes
        recipes_data = get_fallback_recipes(pantry_items)
    
    # Get today's date and calculate next 7 days
    today = date.today()
    meal_types = ['Breakfast', 'Lunch', 'Dinner']
    
    # Delete existing meal plans for the next 7 days to avoid duplicates
    for i in range(7):
        day_date = today + timedelta(days=i)
        MealPlan.objects.filter(
            user=request.user,
            date=day_date
        ).delete()
    
    # Create MealPlan entries for each day
    created_meals = []
    for i in range(7):
        day_date = today + timedelta(days=i)
        recipe = recipes_data[i % len(recipes_data)]  # Cycle through recipes if less than 7
        
        # Create one meal per day (rotate through meal types)
        meal_type = meal_types[i % 3]  # Rotate: Breakfast, Lunch, Dinner
        
        # Get recipe_id - ensure it's an integer or None (fallback recipes have string IDs)
        rid = recipe.get('id')
        if rid is not None:
            try:
                rid = int(rid)
            except (ValueError, TypeError):
                rid = None
        
        meal_plan = MealPlan.objects.create(
            user=request.user,
            recipe_name=recipe.get('title', f'Meal {i+1}'),
            recipe_id=rid,
            date=day_date,
            meal_type=meal_type
        )
        created_meals.append(meal_plan)
    
    return JsonResponse({
        'success': True,
        'message': f'Generated {len(created_meals)} meals for the next 7 days!',
        'meals_count': len(created_meals)
    })

# This is for the Recipe viewing page and Recipe Input page
def recipe_view(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
 
    # If the recipe is not public, only the owner can view it
    if not recipe.is_public:
        if not request.user.is_authenticated or request.user != recipe.user:
            raise PermissionDenied
 
    steps = list(recipe.steps.order_by('order').values_list('text', flat=True))
 
    ingredients = [
        {
            "display": " ".join(
                part for part in (
                    (i.quantity or "").strip(),
                    (i.unit or "").strip(),
                    (i.name or "").strip(),
                ) if part
            ),
            "name": i.name.strip().lower(),
        }
        for i in recipe.ingredients.all()
    ]
 
    # Build a set of pantry ingredient names (lowercase) for the current user
    if request.user.is_authenticated:
        pantry_names = set(
            request.user.pantry_items.values_list('ingredient_name', flat=True)
        )
        pantry_names = {name.lower() for name in pantry_names}
    else:
        pantry_names = set()
 
    # Check if current user has bookmarked this recipe (efficient single query)
    is_saved_by_user = False
    if request.user.is_authenticated:
        is_saved_by_user = recipe.favorites.filter(id=request.user.id).exists()

    return render(request, "recipe_view.html", {
        "recipe": recipe,
        "steps_json": steps,
        "ingredients_json": ingredients,
        "pantry_names_json": list(pantry_names),
        "is_saved_by_user": is_saved_by_user,
    })
 
@login_required
def create_recipe(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        is_public = request.POST.get("is_public") == "on"
        image = request.FILES.get("image")

        #Image upload checking for proper format 
        # MIME check

        if image.content_type not in ["image/jpeg", "image/png"]:
            return render(request, "create_recipe.html", {
                "error": "Only JPEG and PNG images are allowed.",
                "post_data": request.POST,
            })
        # Pillow check
        try:
            img = Image.open(image)
            if img.format not in ["JPEG", "PNG"]:
                return render(request, "create_recipe.html", {
                "error": "Only JPEG and PNG formats are allowed.",
                "post_data": request.POST,
            })
            image.seek(0)
        except Exception:
            return render(request, "create_recipe.html", {
                "error": "Invalid image file.",
                "post_data": request.POST,
            })
    
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
            is_public=is_public,
        )
        if image:
            recipe.image = image
            recipe.save()

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

@login_required
def my_recipes(request):
    """Display a list of the current user's recipes"""
    user_recipes = request.user.recipes.order_by('-created_date')
    return render(request, 'home/my-recipes.html', {'recipes': user_recipes})

@login_required
def delete_recipe(request, recipe_id):
    recipe = get_object_or_404(request.user.recipes, id=recipe_id)
    if request.method == "POST":
        recipe.delete()
        return redirect("/my-recipes/")
    return render(request, "home/delete_recipe.html", {"recipe": recipe})

    #Create a new session
    session = ChatSession.objects.create(
        user=request.user,
        spoonacular_context=spoonacular_recipes,
        pantry_context=pantry_items,
    )

#Social feed view
@login_required
def social_feed(request):
    """Display a feed of all public recipes from all users, newest first"""
    public_recipes = Recipe.objects.filter(is_public=True).order_by('-created_date')
    return render(request, 'home/social_feed.html', {'public_recipes': public_recipes})

#Render the ChefBot chat page and starts new session and then prompts it
#with the newly pulled spoonacular recipes and saved recipes
@login_required
def aiChefBot_view(request):

    #Getting the spoonacular recipes
    spoonacular_recipes = []
    pantry_items = list(request.user.pantry_items.values_list('ingredient_name', flat=True))
    session = ChatSession.objects.filter(user=request.user).first()
    if pantry_items:
        try:
            from .spoonacular import spoonacular_get
            raw = spoonacular_get("recipes/findByIngredients", {
                "ingredients": ','.join(pantry_items),
                "number": 5,
                "ranking": 1,
                "ignorePantry": False,
            })
            for r in raw:
                spoonacular_recipes.append({
                    'title': r.get('title'),
                    'used_ingredients': [i['name'] for i in r.get('usedIngredients', [])],
                    'missed_ingredients': [i['name'] for i in r.get('missedIngredients', [])],
                })
        #If Spoonacular is unavailable, continue without it
        except Exception:
            spoonacular_recipes = []

    #Get saved recipes
    saved_recipes = []
    for recipe in request.user.recipes.prefetch_related('ingredients').all():
        saved_recipes.append({
            'title': recipe.title,
            'ingredients': list(recipe.ingredients.values('quantity', 'unit', 'name')),
        })


    return render(request, 'home/aiChefBot.html', {
        'session_id': session.id,
        'spoonacular_recipes': spoonacular_recipes,
        'saved_recipes': saved_recipes,
    })

#Take in the user message and append it to the search history
@login_required
@require_POST
def aiChefBot_chat(request):

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')

        if not user_message:
            return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

        if not session_id:
            return JsonResponse({'error': 'Session ID is required.'}, status=400)

        #Load chat session
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Chat session not found.'}, status=404)

        #Save the user's message
        ChatMessage.objects.create(
            session=session,
            role='user',
            content=user_message,
        )

        #Build full conversation history
        conversation_history = session.get_history()

        #Build saved recipes context
        saved_recipes = []
        for recipe in request.user.recipes.prefetch_related('ingredients').all():
            saved_recipes.append({
                'title': recipe.title,
                'ingredients': list(recipe.ingredients.values('quantity', 'unit', 'name')),
            })
        #Get pantry items
        pantry_items = list(request.user.pantry_items.values_list('ingredient_name', flat=True))

        #Call OpenAI
        reply = call_openai(
            conversation_history=conversation_history,
            spoonacular_recipes=session.spoonacular_context,
            saved_recipes=saved_recipes,
            pantry_items=pantry_items, 
        )

        #Save ChefBot's response
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=reply,
        )

        return JsonResponse({'reply': reply})

    except Exception as e:
        return JsonResponse({'error': f'Something went wrong: {str(e)}'}, status=500)
 
@login_required
@require_GET
def find_kroger_stores(request):
    """Returns a JSON list of nearby Kroger stores given a lat/lon from the browser"""
    lat = request.GET.get("lat")
    lon = request.GET.get("lon")
    ingredient = request.GET.get('ingredient')

    if not lat or not lon or not ingredient:
        return JsonResponse({"error": "lat, lon, and ingredient are required"}, status=400)

    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        return JsonResponse({"error": "lat and lon must be valid numbers"}, status=400)

    try:
        from .kroger import get_nearby_stores
        stores = get_nearby_stores(lat, lon)
        return JsonResponse({"stores": stores})
    except Exception as e:
        return JsonResponse({"error": f"Kroger API request failed: {str(e)}"}, status=502)

@login_required
@require_POST
def toggle_favorite(request, recipe_id):
    """Toggle a recipe in user's favorites"""
    recipe = get_object_or_404(Recipe, id=recipe_id)
    if recipe.favorites.filter(id=request.user.id).exists():
        recipe.favorites.remove(request.user)
        saved = False
    else:
        recipe.favorites.add(request.user)
        saved = True
    
    return JsonResponse({
        'saved': saved,
        'recipe_id': recipe.id
    })

@login_required
def favorites_list(request):
    """Display user's favorited recipes"""
    favorite_recipes = request.user.favorite_recipes.all().select_related('user').prefetch_related('ratings')
    return render(request, 'home/favorites_list.html', {'favorite_recipes': favorite_recipes})
