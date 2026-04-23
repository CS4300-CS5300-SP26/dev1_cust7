from behave import given, when, then
import json
from django.urls import reverse
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import Client
from home.models import Pantry, MealPlan

# 21 meals: 7 days x 3 meal types
MOCK_AI_MEALS = [
    {
        "day": day,
        "meal_type": meal_type,
        "recipe_name": f"Mock {meal_type} Day {day}",
        "calories": 500,
        "protein": 30,
        "fat": 15,
        "carbs": 50,
    }
    for day in range(1, 8)
    for meal_type in ["Breakfast", "Lunch", "Dinner"]
]


def post_generate(context, payload):
    """Helper to POST to generate_meal_plan with mocked OpenAI."""
    with patch("home.views.generate_meal_plan_with_ai", return_value=MOCK_AI_MEALS):
        context.response = context.client.post(
            reverse("generate_meal_plan"),
            data=json.dumps(payload),
            content_type="application/json",
        )


@given("I am a logged-in user")
def step_logged_in_user(context):

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

    for ingredient in [ingredient1, ingredient2]:
        Pantry.objects.get_or_create(user=context.user, ingredient_name=ingredient)


@given("my pantry is currently empty")
def step_empty_pantry(context):

    # Clear any existing pantry items for this user
    Pantry.objects.filter(user=context.user).delete()


@given("I have generated a weekly meal plan")
def step_generated_meal_plan(context):
    """Actually generate a meal plan by calling the real endpoint"""

    post_generate(context, {"use_pantry": False})

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

    # Always re-login to ensure session is valid
    context.client.login(username="testuser", password="testpass123")
    context.user = User.objects.get(username="testuser")
    post_generate(context, {"use_pantry": True})


@when("I return to the calendar page")
def step_return_to_calendar(context):
    """Navigate back to the calendar page"""
    # Ensure user is logged in (calendar_view requires login)
    if not hasattr(context, "user") or not context.user.is_authenticated:
        user = User.objects.get(username="testuser")
        context.client.login(username="testuser", password="testpass123")
        context.user = user
    context.response = context.client.get("/calendar/")


@when(
    'I generate a meal plan with calories "{calories}" protein "{protein}" fat "{fat}" carbs "{carbs}" cuisine "{cuisine}" and pantry on'
)
def step_generate_all_fields_pantry_on(context, calories, protein, fat, carbs, cuisine):
    post_generate(
        context,
        {
            "calories": int(calories),
            "protein": int(protein),
            "fat": int(fat),
            "carbs": int(carbs),
            "cuisine": cuisine,
            "use_pantry": True,
        },
    )


@when(
    'I generate a meal plan with calories "{calories}" protein "{protein}" fat "{fat}" carbs "{carbs}" cuisine "{cuisine}" and pantry off'
)
def step_generate_all_fields_pantry_off(
    context, calories, protein, fat, carbs, cuisine
):
    post_generate(
        context,
        {
            "calories": int(calories),
            "protein": int(protein),
            "fat": int(fat),
            "carbs": int(carbs),
            "cuisine": cuisine,
            "use_pantry": False,
        },
    )


@when("I generate a meal plan with no inputs and pantry off")
def step_generate_no_inputs(context):
    post_generate(
        context,
        {
            "use_pantry": False,
        },
    )


@when(
    'I generate a meal plan with calories "{calories}" protein "{protein}" fat "{fat}" carbs "{carbs}" and no cuisine'
)
def step_generate_only_macros(context, calories, protein, fat, carbs):
    post_generate(
        context,
        {
            "calories": int(calories),
            "protein": int(protein),
            "fat": int(fat),
            "carbs": int(carbs),
            "cuisine": None,
            "use_pantry": False,
        },
    )


@when('I generate a meal plan with cuisine "{cuisine}" and no macros')
def step_generate_only_cuisine(context, cuisine):
    post_generate(
        context,
        {
            "calories": None,
            "protein": None,
            "fat": None,
            "carbs": None,
            "cuisine": cuisine,
            "use_pantry": False,
        },
    )


@when("I generate a meal plan with pantry on and no other inputs")
def step_generate_pantry_on_no_inputs(context):
    # Do NOT mock here — we want the real view to reject empty pantry
    context.response = context.client.post(
        reverse("generate_meal_plan"),
        data=json.dumps({"use_pantry": True}),
        content_type="application/json",
    )


@then("I should see {count:d} meals on the calendar grid")
def step_see_meals_on_calendar(context, count):
    """Verify the correct number of meals are displayed"""

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
