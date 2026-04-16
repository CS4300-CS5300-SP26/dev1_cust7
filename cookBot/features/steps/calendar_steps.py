from behave import given, when, then
import json
from django.urls import reverse


@given("I am a logged-in user")
def step_logged_in_user(context):
    from django.contrib.auth.models import User
    from django.test import Client

    # Create or get test user
    user, created = User.objects.get_or_create(username="testuser")
    if created:
        user.set_password("testpass123")
        user.save()

    # Create a client and log in
    context.client = Client()
    context.client.login(username="testuser", password="testpass123")
    context.user = user


@given('I have "{ingredient1}" and "{ingredient2}" in my pantry')
def step_have_ingredients(context, ingredient1, ingredient2):
    from home.models import Pantry

    for ingredient in [ingredient1, ingredient2]:
        Pantry.objects.get_or_create(user=context.user, ingredient_name=ingredient)


@given("my pantry is currently empty")
def step_empty_pantry(context):
    from home.models import Pantry

    # Clear any existing pantry items for this user
    Pantry.objects.filter(user=context.user).delete()


@given("I have generated a weekly meal plan")
def step_generated_meal_plan(context):
    """Actually generate a meal plan by calling the real endpoint"""
    from home.models import MealPlan
    from django.urls import reverse

    # Call the real generate_meal_plan endpoint to create actual database entries
    context.client.post(reverse("generate_meal_plan"))

    # Store the generated meals for later verification
    meals = MealPlan.objects.filter(user=context.user)
    context.saved_meal_plan = {
        "meals": [
            {"day": meal.date.strftime("%A"), "meal": meal.recipe_name}
            for meal in meals
        ]
    }


@when('I click "Generate Weekly Plan"')
def step_click_generate(context):
    """Simulate clicking the generate button by calling the meal plan generator"""
    from django.contrib.auth.models import User

    if (
        not hasattr(context, "user")
        or not User.objects.filter(username="testuser").exists()
    ):
        user, created = User.objects.get_or_create(username="testuser")
        if created:
            user.set_password("testpass123")
            user.save()

    # Always re-login to ensure session is valid
    context.client.login(username="testuser", password="testpass123")
    context.user = User.objects.get(username="testuser")

    # POST to the real generate_meal_plan endpoint (with CSRF token)
    context.response = context.client.post(reverse("generate_meal_plan"))


@when("I return to the calendar page")
def step_return_to_calendar(context):
    """Navigate back to the calendar page"""
    # Ensure user is logged in (calendar_view requires login)
    from django.contrib.auth.models import User

    if not hasattr(context, "user") or not context.user.is_authenticated:
        user = User.objects.get(username="testuser")
        context.client.login(username="testuser", password="testpass123")
        context.user = user
    context.response = context.client.get("/calendar/")


@then("I should see {count:d} meals on the calendar grid")
def step_see_meals_on_calendar(context, count):
    """Verify the correct number of meals are displayed"""
    from home.models import MealPlan

    # Query the database to verify the correct number of meals were created
    meals = MealPlan.objects.filter(user=context.user)
    assert len(meals) == count, f"Expected {count} meals in database, got {len(meals)}"

    # Also verify the response was successful (either from generate or calendar view)
    assert (
        context.response.status_code == 200
    ), f"Expected 200, got {context.response.status_code}"


@then('I should see a warning message "{message}"')
def step_see_warning_message(context, message):
    """Verify a warning message is displayed"""
    # Check if response is JSON
    try:
        data = json.loads(context.response.content)
        error_msg = data.get("error", "") or data.get("message", "")
        assert (
            message.lower() in error_msg.lower()
        ), f"Expected '{message}' in response, got: {error_msg}"
    except json.JSONDecodeError:
        # If not JSON, check HTML content
        content = context.response.content.decode("utf-8")
        assert (
            message.lower() in content.lower()
        ), f"Expected '{message}' in page content"


@then("the previously generated meals should still be visible")
def step_meals_still_visible(context):
    """Verify that previously generated meals persist in the database"""
    from home.models import MealPlan

    # Query the database directly to verify meals exist for this user
    meals = MealPlan.objects.filter(user=context.user)
    assert meals.exists(), "No meal plans found in database for user"
    assert len(meals) > 0, f"Expected meals to persist, but found {len(meals)} meals"

    # If we have saved meal plan data, verify the meal names match
    if hasattr(context, "saved_meal_plan"):
        meal_plan = context.saved_meal_plan
        db_meal_names = [meal.recipe_name for meal in meals]

        for meal in meal_plan["meals"]:
            found = any(meal["meal"] in db_name for db_name in db_meal_names)
            assert (
                found
            ), f"Meal '{meal['meal']}' not found in database meals: {db_meal_names}"
