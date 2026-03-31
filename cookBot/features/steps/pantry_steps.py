from behave import given, when, then
import json


@given('"{ingredient}" is already in my pantry')
def step_ingredient_in_pantry(context, ingredient):
    from django.contrib.auth.models import User
    from home.models import Pantry

    user = User.objects.get(username='testuser')
    Pantry.objects.get_or_create(user=user, ingredient_name=ingredient)


@when('I visit the pantry page')
def step_visit_pantry(context):
    context.response = context.client.get('/pantry/')


@when('I add the ingredient "{ingredient}" to my pantry')
def step_add_ingredient(context, ingredient):
    context.response = context.client.post(
        '/pantry/add/',
        data=json.dumps({'ingredient_name': ingredient}),
        content_type='application/json'
    )


@when('I delete "{ingredient}" from my pantry')
def step_delete_ingredient(context, ingredient):
    from django.contrib.auth.models import User
    from home.models import Pantry

    user = User.objects.get(username='testuser')
    item = Pantry.objects.get(user=user, ingredient_name=ingredient)
    context.response = context.client.post(f'/pantry/delete/{item.id}/')


@when('I search for recipes by pantry')
def step_search_recipes(context):
    context.response = context.client.get('/pantry/search-recipes/')


@when('I request fallback recipes')
def step_request_fallback_recipes(context):
    from home.views import get_fallback_recipes
    from django.contrib.auth.models import User
    from home.models import Pantry

    user = User.objects.get(username='testuser')
    pantry_items = Pantry.objects.filter(user=user).values_list('ingredient_name', flat=True)
    context.fallback_recipes = get_fallback_recipes(pantry_items)


@then('the pantry page should load successfully')
def step_pantry_loads(context):
    assert context.response.status_code == 200


@then('"{ingredient}" should exist in the pantry')
def step_ingredient_exists(context, ingredient):
    from home.models import Pantry

    assert Pantry.objects.filter(ingredient_name=ingredient).exists()


@then('"{ingredient}" should not exist in the pantry')
def step_ingredient_gone(context, ingredient):
    from home.models import Pantry

    assert not Pantry.objects.filter(ingredient_name=ingredient).exists()


@then('I should receive a 400 error response')
def step_400_response(context):
    assert context.response.status_code == 400


@then('I should see the message "{message}"')
def step_see_message(context, message):
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"
    data = json.loads(context.response.content)
    assert message in str(data)


@then('I should receive at least one recipe result')
def step_has_recipes(context):
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"
    data = json.loads(context.response.content)
    assert len(data.get('recipes', [])) >= 1


@then('I should still receive recipe suggestions')
def step_has_fallback_recipes(context):
    assert len(context.fallback_recipes) > 0