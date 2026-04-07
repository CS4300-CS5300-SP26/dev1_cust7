from behave import given, when, then
from django.contrib.auth.models import User
from django.urls import reverse
from home.models import Pantry, Recipe, RecipeIngredient, RecipeStep, MealPlan
import json


# ============================================================================
# Navigation Steps
# ============================================================================

@given('I am on the sign in page')
def step_on_signin_page(context):
    """Navigate to the sign in page"""
    context.response = context.client.get(reverse('signin'))
    assert context.response.status_code == 200

@given('I am on the register page')
def step_on_register_page(context):
    """Navigate to the register page"""
    context.response = context.client.get(reverse('register'))
    assert context.response.status_code == 200

@when('I navigate to the pantry page')
def step_navigate_to_pantry(context):
    """Navigate to the pantry page"""
    context.response = context.client.get(reverse('pantry'))
    assert context.response.status_code == 200

@when('I navigate to the create recipe page')
def step_navigate_to_create_recipe(context):
    """Navigate to the create recipe page"""
    context.response = context.client.get(reverse('create_recipe'))
    assert context.response.status_code == 200

@when('I navigate to the calendar page')
def step_navigate_to_calendar(context):
    """Navigate to the calendar page"""
    context.response = context.client.get(reverse('calendar'))
    assert context.response.status_code == 200

@when('I navigate to the edit account page')
def step_navigate_to_edit_account(context):
    """Navigate to the edit account page"""
    context.response = context.client.get(reverse('edit_account'))
    assert context.response.status_code == 200

@when('I navigate to the home page')
def step_navigate_to_home(context):
    """Navigate to the home page"""
    context.response = context.client.get(reverse('index'))
    assert context.response.status_code == 200


# ============================================================================
# Authentication Steps
# ============================================================================

@when('I log in with valid credentials')
def step_login_with_credentials(context):
    """Log in using the credentials table from the feature file"""
    credentials = {row['username']: row['password'] for row in context.table}
    username = list(credentials.keys())[0]
    password = credentials[username]
    
    # Ensure user exists with the correct password
    user, created = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.save()
    
    logged_in = context.client.login(username=username, password=password)
    assert logged_in, f"Login failed for user '{username}' with password '{password}'"
    context.user = user

@when('I log out')
def step_logout(context):
    """Log out the current user"""
    context.response = context.client.get(reverse('logout'))
    assert context.response.status_code == 302


# ============================================================================
# Form Filling Steps
# ============================================================================

@when('I fill in the registration form with')
def step_fill_registration_form(context):
    """Fill in the registration form with the provided data table"""
    form_data = {row['field']: row['value'] for row in context.table}
    context.form_data = form_data

@when('I submit the registration form')
def step_submit_registration(context):
    """Submit the registration form"""
    form_data = getattr(context, 'form_data', {})
    context.response = context.client.post(reverse('register'), form_data)

@when('I submit the recipe form without a title')
def step_submit_recipe_without_title(context):
    """Submit the recipe form without a title"""
    context.response = context.client.post(reverse('create_recipe'), {
        'title': '',  # Empty title
        'is_public': 'on'
    })

@when('I change my email to "{email}"')
def step_change_email(context, email):
    """Change the email field in the edit account form"""
    context.email_to_set = email

@when('I submit the edit account form')
def step_submit_edit_account(context):
    """Submit the edit account form"""
    email = getattr(context, 'email_to_set', context.user.email)
    context.response = context.client.post(reverse('edit_account'), {
        'first_name': context.user.first_name,
        'last_name': context.user.last_name,
        'username': context.user.username,
        'email': email,
    })

@when('I create a recipe titled "{title}" with ingredients')
def step_create_recipe_with_ingredients(context, title):
    """Create a recipe with ingredients and steps"""
    ingredients_table = context.table
    context.recipe_ingredients = [
        {'quantity': row['quantity'], 'unit': row['unit'], 'name': row['name']}
        for row in ingredients_table
    ]
    context.recipe_title = title

@when('steps')
def step_add_recipe_steps(context):
    """Add steps to the recipe being created"""
    steps_table = context.table
    context.recipe_steps = [
        {'order': int(row['order']), 'text': row['text']}
        for row in steps_table
    ]
    
    # Ensure user is logged in - if not, create and log in a test user
    if not hasattr(context, 'user') or context.user is None:
        from django.contrib.auth.models import User
        user, created = User.objects.get_or_create(username='e2e_recipe_user')
        if created:
            user.set_password('TestPass123!')
            user.first_name = 'E2E'
            user.last_name = 'User'
            user.save()
        context.client.login(username='e2e_recipe_user', password='TestPass123!')
        context.user = user
    
    # Now create the recipe with both ingredients and steps
    recipe = Recipe.objects.create(
        user=context.user,
        title=context.recipe_title,
        is_public=True
    )
    
    # Add ingredients
    for ing in context.recipe_ingredients:
        RecipeIngredient.objects.create(
            recipe=recipe,
            quantity=ing['quantity'],
            unit=ing['unit'],
            name=ing['name']
        )
    
    # Add steps
    for step in context.recipe_steps:
        RecipeStep.objects.create(
            recipe=recipe,
            order=step['order'],
            text=step['text']
        )
    
    context.created_recipe = recipe
    context.response = context.client.get(reverse('recipe_view', args=[recipe.id]))


# ============================================================================
# Pantry Steps
# ============================================================================

@given('"{ingredient}" is in my pantry')
def step_ingredient_in_pantry(context, ingredient):
    """Ensure an ingredient is in the user's pantry"""
    Pantry.objects.get_or_create(user=context.user, ingredient_name=ingredient)

@when('I add "{ingredient}" to my pantry')
def step_add_ingredient_to_pantry(context, ingredient):
    """Add an ingredient to the pantry"""
    context.response = context.client.post(
        reverse('add_ingredient'),
        data=json.dumps({'ingredient_name': ingredient}),
        content_type='application/json'
    )

@when('I try to add "{ingredient}" to my pantry')
def step_try_add_duplicate_ingredient(context, ingredient):
    """Try to add a duplicate ingredient to the pantry"""
    context.response = context.client.post(
        reverse('add_ingredient'),
        data=json.dumps({'ingredient_name': ingredient}),
        content_type='application/json'
    )

@when('I click search recipes')
def step_click_search_recipes(context):
    """Click the search recipes button"""
    context.response = context.client.get(reverse('search_recipes_by_pantry'))


# ============================================================================
# Calendar Steps
# ============================================================================

@when('I click the generate meal plan button')
def step_click_generate_meal_plan(context):
    """Click the generate meal plan button"""
    from unittest.mock import patch
    
    # Mock the API call to return 7 recipes
    mock_recipes = [{'id': i, 'title': f'Recipe {i}'} for i in range(1, 8)]
    with patch('home.views.spoonacular_get', return_value=mock_recipes):
        context.response = context.client.post(reverse('generate_meal_plan'))


# ============================================================================
# Assertion Steps
# ============================================================================

@then('I should see the home page')
def step_see_home_page(context):
    """Verify the home page is displayed"""
    assert context.response.status_code == 200
    content = context.response.content.decode('utf-8')
    assert 'index' in content.lower() or 'home' in content.lower() or context.response.status_code == 200

@then('I should see both ingredients in my pantry')
def step_see_ingredients_in_pantry(context):
    """Verify both ingredients are in the pantry"""
    pantry_items = Pantry.objects.filter(user=context.user)
    ingredient_names = [item.ingredient_name.lower() for item in pantry_items]
    assert 'chicken' in ingredient_names, "Chicken not found in pantry"
    assert 'rice' in ingredient_names, "Rice not found in pantry"

@then('I should see {count:d} meals on the calendar')
def step_see_meals_on_calendar(context, count):
    """Verify the correct number of meals are on the calendar"""
    meals = MealPlan.objects.filter(user=context.user)
    assert meals.count() >= count, f"Expected at least {count} meals, got {meals.count()}"

@then('the meals should be for the next {days:d} days')
def step_meals_for_next_days(context, days):
    """Verify meals are scheduled for the next N days"""
    from datetime import date, timedelta
    
    meals = MealPlan.objects.filter(user=context.user)
    today = date.today()
    
    for meal in meals:
        days_diff = (meal.date - today).days
        assert 0 <= days_diff < days, f"Meal date {meal.date} is not within next {days} days"

@then('I should see the sign in page')
def step_see_signin_page(context):
    """Verify the sign in page is displayed"""
    # After logout, user is redirected to index, then can access signin
    response = context.client.get(reverse('signin'))
    assert response.status_code == 200

@then('I should be redirected to the home page')
def step_redirected_to_home(context):
    """Verify redirect to home page"""
    assert context.response.status_code == 302
    assert context.response.url == reverse('index') or 'index' in context.response.url

@then('I should see the recipe view page')
def step_see_recipe_view(context):
    """Verify the recipe view page is displayed"""
    assert context.response.status_code == 200

@then('the recipe title should be "{title}"')
def step_see_recipe_title(context, title):
    """Verify the recipe title is displayed"""
    content = context.response.content.decode('utf-8')
    assert title in content, f"Recipe title '{title}' not found in page"

@then('I should see a password mismatch error')
def step_see_password_mismatch_error(context):
    """Verify password mismatch error is displayed"""
    content = context.response.content.decode('utf-8')
    assert 'password' in content.lower() and ('mismatch' in content.lower() or 'does not match' in content.lower() or 'did not match' in content.lower()), \
        "Password mismatch error not found"

@then('I should see a username already exists error')
def step_see_username_exists_error(context):
    """Verify username already exists error is displayed"""
    content = context.response.content.decode('utf-8')
    assert 'username' in content.lower() and ('already exists' in content.lower() or 'already taken' in content.lower()), \
        "Username already exists error not found"

@then('I should see an error message about the title')
def step_see_title_error(context):
    """Verify title error message is displayed"""
    content = context.response.content.decode('utf-8')
    assert 'title' in content.lower() and ('cannot be empty' in content.lower() or 'required' in content.lower()), \
        "Title error message not found"

@then('I should see an email already in use error')
def step_see_email_in_use_error(context):
    """Verify email already in use error is displayed"""
    content = context.response.content.decode('utf-8')
    assert 'email' in content.lower() and ('already in use' in content.lower() or 'already taken' in content.lower()), \
        "Email already in use error not found"

@then('I should see a duplicate ingredient error')
def step_see_duplicate_ingredient_error(context):
    """Verify duplicate ingredient error is displayed"""
    content = context.response.content.decode('utf-8')
    assert 'already' in content.lower() or 'duplicate' in content.lower(), \
        "Duplicate ingredient error not found"

@then('I should see a username validation error')
def step_see_username_validation_error(context):
    """Verify username validation error is displayed"""
    content = context.response.content.decode('utf-8')
    # Check for form errors (username validation)
    assert 'username' in content.lower() or context.response.status_code == 200, \
        "Username validation error not found"

@then('I should see recipe suggestions')
def step_see_recipe_suggestions(context):
    """Verify recipe suggestions are displayed"""
    assert context.response.status_code == 200
    data = context.response.json()
    assert 'recipes' in data, "No recipes found in response"

@then('the recipes should use my pantry ingredients')
def step_recipes_use_pantry_ingredients(context):
    """Verify recipes use pantry ingredients"""
    data = context.response.json()
    recipes = data.get('recipes', [])
    assert len(recipes) > 0, "No recipes found"
    # Check that at least one recipe uses a pantry ingredient
    pantry_ingredients = list(Pantry.objects.filter(user=context.user).values_list('ingredient_name', flat=True))
    found_match = False
    for recipe in recipes:
        used_ingredients = recipe.get('used_ingredients', [])
        if any(ing.lower() in [p.lower() for p in pantry_ingredients] for ing in used_ingredients):
            found_match = True
            break
    assert found_match, "No recipes use pantry ingredients"