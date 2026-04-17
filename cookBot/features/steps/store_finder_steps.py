from behave import given, when, then
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import Client
from home.models import Recipe, RecipeIngredient
from django.core.cache import cache
import json
import urllib.error

MOCK_TOKEN_RESPONSE = {
    "access_token": "fake-token-abc123",
    "expires_in": 1800,
    "token_type": "Bearer",
}

MOCK_KROGER_STORE_RESPONSE = {
    "data": [
        {
            "locationId": "01400943",
            "name": "Kroger",
            "address": {
                "addressLine1": "123 Main St",
                "city": "Denver",
                "state": "CO",
                "zipCode": "80203",
            },
            "geolocation": {"distanceInMiles": 1.2},
            "phone": "303-555-0101",
        },
    ]
}

MOCK_KROGER_EMPTY_RESPONSE = {"data": []}


def make_mock_response(json_data):
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.read.return_value = json.dumps(json_data).encode()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


# --- GIVEN ---


@given('I am a logged in user viewing a recipe with missing ingredients')
def step_logged_in_viewing_recipe(context):
    cache.clear()
    context.client = Client()
    User.objects.filter(username='testuser').delete()
    user = User.objects.create_user(username='testuser', password='testpass123')
    context.client.post('/signin/', {'username': 'testuser', 'password': 'testpass123'})
    recipe = Recipe.objects.create(user=user, title='Paella', is_public=False)
    RecipeIngredient.objects.create(recipe=recipe, name='saffron', quantity='1', unit='pinch')
    context.recipe = recipe
    context.user = user

@given('I am a logged in user with saffron in their pantry viewing a recipe with saffron')
def step_logged_in_with_saffron_in_pantry(context):
    cache.clear()
    context.client = Client()
    User.objects.filter(username='testuser').delete()
    user = User.objects.create_user(username='testuser', password='testpass123')
    context.client.post('/signin/', {'username': 'testuser', 'password': 'testpass123'})
    recipe = Recipe.objects.create(user=user, title='Paella', is_public=False)
    RecipeIngredient.objects.create(recipe=recipe, name='saffron', quantity='1', unit='pinch')
    user.pantry_items.create(ingredient_name='saffron')
    context.recipe = recipe

@given('I am a logged in user with Saffron stored with a capital S')
def step_logged_in_with_capitalised_pantry_item(context):
    cache.clear()
    context.client = Client()
    User.objects.filter(username='testuser').delete()
    user = User.objects.create_user(username='testuser', password='testpass123')
    context.client.post('/signin/', {'username': 'testuser', 'password': 'testpass123'})
    recipe = Recipe.objects.create(user=user, title='Paella', is_public=False)
    RecipeIngredient.objects.create(recipe=recipe, name='saffron', quantity='1', unit='pinch')
    user.pantry_items.create(ingredient_name='Saffron')  # capital S
    context.recipe = recipe


# --- WHEN ---

@when('I request nearby Kroger stores for a missing ingredient')
def step_request_stores_unauthenticated(context):
    context.response = context.client.get(
        '/kroger/stores/',
        {'lat': 38.9099, 'lon': -104.7266, 'ingredient': 'saffron'}
    )

@when('I request nearby stores without providing a location')
def step_request_stores_no_location(context):
    context.response = context.client.get(
        '/kroger/stores/',
        {'ingredient': 'saffron'}
    )

@when('I request nearby stores without providing an ingredient')
def step_request_stores_no_ingredient(context):
    context.response = context.client.get(
        '/kroger/stores/',
        {'lat': 38.9099, 'lon': -104.7266}
    )

@when('I request nearby Kroger stores with a valid location and ingredient')
def step_request_stores_valid(context):
    with patch('home.kroger.urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_TOKEN_RESPONSE),
            make_mock_response(MOCK_KROGER_STORE_RESPONSE),
        ]
        context.response = context.client.get(
            '/kroger/stores/',
            {'lat': 38.9099, 'lon': -104.7266, 'ingredient': 'saffron'}
        )

@when('I request nearby Kroger stores in a remote location')
def step_request_stores_remote(context):
    with patch('home.kroger.urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_TOKEN_RESPONSE),
            make_mock_response(MOCK_KROGER_EMPTY_RESPONSE),
        ]
        context.response = context.client.get(
            '/kroger/stores/',
            {'lat': 71.2906, 'lon': -156.7887, 'ingredient': 'saffron'}
        )

@when('the Kroger API is unavailable')
def step_kroger_api_unavailable(context):
    with patch('home.kroger.urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        context.response = context.client.get(
            '/kroger/stores/',
            {'lat': 38.9099, 'lon': -104.7266, 'ingredient': 'saffron'}
        )

@when('I load the recipe detail page')
def step_load_recipe_detail(context):
    context.response = context.client.get(
        f'/recipe/{context.recipe.id}/',
        follow=True  # follow any redirects so context is populated
    )
# --- THEN ---

@then('I should receive a 200 response with a list of nearby stores')
def step_receive_200_with_stores(context):
    assert context.response.status_code == 200
    data = json.loads(context.response.content)
    assert 'stores' in data
    assert len(data['stores']) > 0

@then('each store should have a name, address, and distance')
def step_stores_have_required_fields(context):
    data = json.loads(context.response.content)
    for store in data['stores']:
        assert 'name' in store
        assert 'address' in store
        assert 'distance' in store

@then('I should receive a 200 response with an empty store list')
def step_receive_200_empty(context):
    assert context.response.status_code == 200
    data = json.loads(context.response.content)
    assert data['stores'] == []

@then('I should receive a 502 error response')
def step_receive_502(context):
    assert context.response.status_code == 502
    data = json.loads(context.response.content)
    assert 'error' in data

@then('each ingredient should have a display field and a name field')
def step_ingredients_have_correct_shape(context):
    assert context.response.status_code == 200
    content = context.response.content.decode('utf-8')
    # ingredients-data script tag is rendered by the view into the page
    assert 'ingredients-data' in content, "ingredients-data script tag missing from page"
    import re, json
    match = re.search(r'id="ingredients-data"[^>]*>(\[.*?\])<', content, re.DOTALL)
    assert match, "Could not find ingredients JSON in page"
    ingredients = json.loads(match.group(1))
    assert len(ingredients) > 0
    for ing in ingredients:
        assert 'display' in ing, f"Missing 'display' in {ing}"
        assert 'name' in ing,    f"Missing 'name' in {ing}"

@then('the pantry names should include saffron')
def step_pantry_names_include_saffron(context):
    assert context.response.status_code == 200
    content = context.response.content.decode('utf-8')
    import re, json
    match = re.search(r'id="pantry-data"[^>]*>(\[.*?\])<', content, re.DOTALL)
    assert match, "Could not find pantry-data JSON in page"
    pantry_names = json.loads(match.group(1))
    assert 'saffron' in pantry_names

@then('the pantry names should contain saffron in lowercase')
def step_pantry_names_are_lowercase(context):
    assert context.response.status_code == 200
    content = context.response.content.decode('utf-8')
    import re, json
    match = re.search(r'id="pantry-data"[^>]*>(\[.*?\])<', content, re.DOTALL)
    assert match, "Could not find pantry-data JSON in page"
    pantry_names = json.loads(match.group(1))
    assert 'saffron' in pantry_names
    assert 'Saffron' not in pantry_names