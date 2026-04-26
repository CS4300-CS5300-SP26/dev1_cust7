from behave import given, when, then
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from home.models import Recipe, RecipeRating
import json


# --- GIVEN ---

@given('a public recipe exists')
def step_public_recipe_exists(context):
    User.objects.filter(username='recipeowner').delete()
    owner = User.objects.create_user(username='recipeowner', password='testpass123')
    context.recipe = Recipe.objects.create(
        user=owner,
        title='Test Recipe',
        is_public=True,
    )


@given('that user has created a public recipe')
def step_user_created_public_recipe(context):
    context.recipe = Recipe.objects.create(
        user=context.user,
        title='My Own Recipe',
        is_public=True,
    )


@given('another user has created a private recipe')
def step_another_user_private_recipe(context):
    User.objects.filter(username='privateowner').delete()
    owner = User.objects.create_user(username='privateowner', password='testpass123')
    context.recipe = Recipe.objects.create(
        user=owner,
        title='Private Recipe',
        is_public=False,
    )


@given('a second user has rated that recipe {stars:d} stars')
def step_second_user_rated(context, stars):
    User.objects.filter(username='rater2').delete()
    rater = User.objects.create_user(username='rater2', password='testpass123')
    RecipeRating.objects.update_or_create(
        recipe=context.recipe,
        user=rater,
        defaults={'stars': stars},
    )


@given('the user has already rated that recipe {stars:d} stars')
def step_user_already_rated(context, stars):
    RecipeRating.objects.update_or_create(
        recipe=context.recipe,
        user=context.user,
        defaults={'stars': stars},
    )


# --- WHEN ---


@when('an unauthenticated user submits a rating of {stars:d} for that recipe')
def step_unauth_submits_rating(context, stars):
    client = Client()
    context.response = client.post(
        reverse('rate_recipe', args=[context.recipe.id]),
        data=json.dumps({'stars': stars}),
        content_type='application/json',
    )


@when('the user submits a rating of {stars:d} for that recipe')
def step_user_submits_rating(context, stars):
    context.response = context.client.post(
        reverse('rate_recipe', args=[context.recipe.id]),
        data=json.dumps({'stars': stars}),
        content_type='application/json',
    )


@when('the user submits a rating of {stars:d} for that private recipe')
def step_user_submits_rating_private(context, stars):
    context.response = context.client.post(
        reverse('rate_recipe', args=[context.recipe.id]),
        data=json.dumps({'stars': stars}),
        content_type='application/json',
    )


@when('the user visits the recipe view page')
def step_user_visits_recipe_page(context):
    context.response = context.client.get(
        reverse('recipe_view', args=[context.recipe.id])
    )


# --- THEN ---

@then('the response should indicate success')
def step_response_success(context):
    assert context.response.status_code == 200, \
        f"Expected 200, got {context.response.status_code}"
    data = json.loads(context.response.content)
    assert data.get('success') is True, \
        f"Expected success=True in response, got {data}"


@then('the returned average should be {expected:f}')
def step_returned_average(context, expected):
    data = json.loads(context.response.content)
    assert 'average' in data, f"No 'average' key in response: {data}"
    assert float(data['average']) == expected, \
        f"Expected average {expected}, got {data['average']}"


@then('the returned count should be {expected:d}')
def step_returned_count(context, expected):
    data = json.loads(context.response.content)
    assert 'count' in data, f"No 'count' key in response: {data}"
    assert data['count'] == expected, \
        f"Expected count {expected}, got {data['count']}"


@then('I should receive a 403 error response')
def step_receive_403(context):
    assert context.response.status_code == 403, \
        f"Expected 403, got {context.response.status_code}"


@then('the page should show {stars:d} filled stars')
def step_page_shows_filled_stars(context, stars):
    assert context.response.status_code == 200
    content = context.response.content.decode('utf-8')
    # The template renders star buttons with class="star-btn filled" for
    # stars <= user_rating — count how many filled buttons are in the HTML
    filled_count = content.count('star-btn filled')
    assert filled_count == stars, \
        f"Expected {stars} filled star buttons, found {filled_count}"


@then('the page should display the average rating')
def step_page_shows_average(context):
    assert context.response.status_code == 200
    content = context.response.content.decode('utf-8')
    assert '/ 5' in content, \
        "Expected average rating display (x.x / 5) not found in page"
