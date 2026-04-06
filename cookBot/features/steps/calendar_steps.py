from behave import given, when, then
import json

@given('I am a logged-in user')
def step_logged_in_user(context):
    from django.contrib.auth.models import User
    from django.contrib.auth import login
    from django.test import Client

    # Create or get test user
    user, created = User.objects.get_or_create(username='testuser')
    if created:
        user.set_password('testpass123')
        user.save()

    # Create a client and log in
    context.client = Client()
    context.client.login(username='testuser', password='testpass123')
    context.user = user


@given('I have "{ingredient1}" and "{ingredient2}" in my pantry')
def step_have_ingredients(context, ingredient1, ingredient2):
    from home.models import Pantry

    for ingredient in [ingredient1, ingredient2]:
        Pantry.objects.get_or_create(user=context.user, ingredient_name=ingredient)


@given('my pantry is currently empty')
def step_empty_pantry(context):
    from home.models import Pantry

    # Clear any existing pantry items for this user
    Pantry.objects.filter(user=context.user).delete()


@given('I have generated a weekly meal plan')
def step_generated_meal_plan(context):
    """Simulate generating a meal plan - stores it in context for persistence test"""
    from home.models import Pantry

    # Get user's pantry items
    pantry_items = list(Pantry.objects.filter(user=context.user).values_list('ingredient_name', flat=True))

    # Create mock meal plan data (in real implementation, this would call the API)
    context.meal_plan = {
        'meals': [
            {'day': 'Monday', 'meal': f'{pantry_items[0]} {pantry_items[1]}'},
            {'day': 'Tuesday', 'meal': f'{pantry_items[0]} Stir Fry'},
            {'day': 'Wednesday', 'meal': f'{pantry_items[1]} Bowl'},
            {'day': 'Thursday', 'meal': f'Grilled {pantry_items[0]}'},
            {'day': 'Friday', 'meal': f'{pantry_items[1]} Salad'},
            {'day': 'Saturday', 'meal': f'{pantry_items[0]} Soup'},
            {'day': 'Sunday', 'meal': f'Baked {pantry_items[0]}'},
        ]
    }

    # In a real implementation, this would save to the database
    # For now, store in context for the test
    context.saved_meal_plan = context.meal_plan


@when('I click "Generate Weekly Plan"')
def step_click_generate(context):
    """Simulate clicking the generate button by calling the calendar view"""
    # Ensure user is logged in before calling the endpoint
    from django.contrib.auth.models import User
    if not hasattr(context, 'user') or not User.objects.filter(username='testuser').exists():
        user, created = User.objects.get_or_create(username='testuser')
        if created:
            user.set_password('testpass123')
            user.save()
    
    # Always re-login to ensure session is valid
    context.client.login(username='testuser', password='testpass123')
    context.user = User.objects.get(username='testuser')
    
    # Call the calendar generation endpoint
    context.response = context.client.get('/calendar/generate/')


@when('I return to the calendar page')
def step_return_to_calendar(context):
    """Navigate back to the calendar page"""
    # Ensure user is logged in (calendar_view requires login)
    from django.contrib.auth.models import User
    if not hasattr(context, 'user') or not context.user.is_authenticated:
        user = User.objects.get(username='testuser')
        context.client.login(username='testuser', password='testpass123')
        context.user = user
    context.response = context.client.get('/calendar/')

@then('I should see {count:d} meals on the calendar grid')
def step_see_meals_on_calendar(context, count):
    """Verify the correct number of meals are displayed"""
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"

    # Check if response is JSON
    try:
        data = json.loads(context.response.content)
        meals = data.get('meals', [])
        assert len(meals) == count, f"Expected {count} meals, got {len(meals)}"
    except json.JSONDecodeError:
        # If not JSON, check HTML content
        content = context.response.content.decode('utf-8')
        # Count meal entries in the HTML (adjust selector based on your template)
        meal_count = content.count('class="meal-entry"')
        assert meal_count == count, f"Expected {count} meals in HTML, found {meal_count}"


@then('I should see a warning message "{message}"')
def step_see_warning_message(context, message):
    """Verify a warning message is displayed"""
    # Check if response is JSON
    try:
        data = json.loads(context.response.content)
        error_msg = data.get('error', '') or data.get('message', '')
        assert message.lower() in error_msg.lower(), f"Expected '{message}' in response, got: {error_msg}"
    except json.JSONDecodeError:
        # If not JSON, check HTML content
        content = context.response.content.decode('utf-8')
        assert message.lower() in content.lower(), f"Expected '{message}' in page content"


@then('the previously generated meals should still be visible')
def step_meals_still_visible(context):
    """Verify that previously generated meals persist"""
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"

    # Check if we have saved meal plan data
    if hasattr(context, 'saved_meal_plan'):
        meal_plan = context.saved_meal_plan

        # Check if response is JSON
        try:
            data = json.loads(context.response.content)
            returned_meals = data.get('meals', [])
            assert len(returned_meals) > 0, "No meals found in response"

            # Verify at least some meals match
            for meal in meal_plan['meals']:
                found = any(meal['meal'] in rm.get('meal', '') for rm in returned_meals)
                assert found, f"Meal '{meal['meal']}' not found in returned meals"
        except json.JSONDecodeError:
            # If not JSON, check HTML content
            content = context.response.content.decode('utf-8')
            for meal in meal_plan['meals']:
                assert meal['meal'] in content, f"Meal '{meal['meal']}' not found in page"
    else:
        # If no saved meal plan, just verify we get a valid response
        assert context.response.status_code == 200