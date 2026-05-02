from behave import given, when, then
from django.urls import reverse
from datetime import date
from home.models import MealPlan


@given("I have no saved meal plans")
def step_no_saved_meal_plans(context):
    MealPlan.objects.filter(user=context.user).delete()
    assert MealPlan.objects.filter(user=context.user).count() == 0


@given("I have {count:d} saved meal plans")
def step_have_saved_meal_plans(context, count):
    MealPlan.objects.filter(user=context.user).delete()
    for i in range(count):
        MealPlan.objects.create(
            user=context.user,
            recipe_name=f"History Meal {i + 1}",
            recipe_id=100 + i,
            date=date(2026, 4, 1 + i),
            meal_type="Dinner",
            calories=500 + i * 50,
            protein=30 + i * 5,
            fat=15 + i * 2,
            carbs=50 + i * 5,
        )
    assert MealPlan.objects.filter(user=context.user).count() == count


@when("I go to the meal plan history page")
def step_go_to_meal_plan_history(context):
    context.response = context.client.get(reverse("meal_plan_history"))
    assert context.response.status_code == 200


@when("I click on the first meal plan in the history")
def step_click_first_meal_plan(context):
    plans = list(MealPlan.objects.filter(user=context.user).order_by("-created_at"))
    assert len(plans) > 0, "No meal plans to click"
    context.clicked_plan = plans[0]
    context.response = context.client.get(
        reverse("meal_plan_detail", args=[context.clicked_plan.id])
    )


@then('I should see "{text}"')
def step_should_see_text(context, text):
    content = context.response.content.decode("utf-8")
    assert text in content, f"Expected '{text}' not found in page content"


@then("I should see {count:d} meal plans listed with their creation dates")
def step_should_see_meal_plans_with_dates(context, count):
    content = context.response.content.decode("utf-8")
    plans = MealPlan.objects.filter(user=context.user).order_by("-created_at")
    assert plans.count() == count, f"Expected {count} plans, got {plans.count()}"
    for plan in plans:
        assert (
            plan.recipe_name in content
        ), f"Recipe name '{plan.recipe_name}' not found"
        date_str = plan.created_at.strftime("%b %d, %Y")
        assert date_str in content, f"Date '{date_str}' not found in content"


@then("I should be on the view page for that meal plan")
def step_should_be_on_view_page(context):
    assert context.response.status_code == 200
    content = context.response.content.decode("utf-8")
    clicked_name = context.clicked_plan.recipe_name
    assert clicked_name in content, f"Expected '{clicked_name}' on view page"
