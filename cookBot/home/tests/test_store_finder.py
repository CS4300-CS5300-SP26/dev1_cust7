import json
import urllib.error
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache
from home.models import Recipe, RecipeIngredient
 
#### Kroger store finder tests ####
#### Mocking pattern matched from existing Spoonacular tests ####
 
# Sample OAuth token response — Kroger requires a client_credentials token
# before every API call, so _get_access_token() is always the first urlopen hit
MOCK_TOKEN_RESPONSE = {
    "access_token": "fake-token-abc123",
    "expires_in": 1800,
    "token_type": "Bearer",
}
 
# Sample data that mimics a real Kroger API location search response
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
            "geolocation": {
                "distanceInMiles": 1.2,
            },
            "phone": "303-555-0101",
        },
        {
            "locationId": "01400944",
            "name": "King Soopers",
            "address": {
                "addressLine1": "456 Elm Ave",
                "city": "Denver",
                "state": "CO",
                "zipCode": "80204",
            },
            "geolocation": {
                "distanceInMiles": 2.5,
            },
            "phone": "303-555-0202",
        },
    ]
}
 
# Sample data that mimics a Kroger API response with no stores nearby
MOCK_KROGER_EMPTY_RESPONSE = {
    "data": []
}
 
 
def make_mock_response(json_data):
    """
    Creates a fake urllib response object that mimics what urlopen returns.
    urllib.request.urlopen is used as a context manager (with statement), so
    the mock needs __enter__ and __exit__ defined to behave the same way.
    read() returns the JSON data encoded as bytes, just like a real HTTP response.
    """
    mock = MagicMock()
    mock.read.return_value = json.dumps(json_data).encode()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock
 
 
class KrogerStoreFinderTests(TestCase):
 
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        self.client.login(username='testuser', password='password123')
 
        # Create a recipe with a missing ingredient to test against
        self.recipe = Recipe.objects.create(
            user=self.user, title='Paella', is_public=False
        )
        RecipeIngredient.objects.create(
            recipe=self.recipe, name='saffron', quantity='1', unit='pinch'
        )
 
    def test_kroger_store_endpoint_requires_login(self):
        """Tests that an unauthenticated user is redirected away from the store finder"""
        unauthenticated_client = Client()
        response = unauthenticated_client.get(
            reverse('find_kroger_stores'),
            {'lat': 38.9099, 'lon': -104.7266, 'ingredient': 'saffron'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/signin', response.url)
 
    def test_kroger_store_endpoint_requires_lat_and_lon(self):
        """Tests that missing location params return a 400 error"""
        response = self.client.get(
            reverse('find_kroger_stores'),
            {'ingredient': 'saffron'}  # lat and lon deliberately omitted
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
 
    def test_kroger_store_endpoint_requires_ingredient(self):
        """Tests that a missing ingredient param returns a 400 error"""
        response = self.client.get(
            reverse('find_kroger_stores'),
            {'lat': 38.9099, 'lon': -104.7266}  # ingredient deliberately omitted
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
 
    @patch('home.kroger.urllib.request.urlopen')
    def test_returns_store_list_for_valid_request(self, mock_urlopen):
        """Tests that a valid request returns a list of nearby stores"""
        # First call: OAuth token, second call: locations endpoint
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_TOKEN_RESPONSE),
            make_mock_response(MOCK_KROGER_STORE_RESPONSE),
        ]
 
        response = self.client.get(
            reverse('find_kroger_stores'),
            {'lat': 38.9099, 'lon': -104.7266, 'ingredient': 'saffron'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('stores', data)
        self.assertEqual(len(data['stores']), 2)
 
    @patch('home.kroger.urllib.request.urlopen')
    def test_returned_stores_have_required_fields(self, mock_urlopen):
        """Tests that each store in the response includes name, address, and distance"""
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_TOKEN_RESPONSE),
            make_mock_response(MOCK_KROGER_STORE_RESPONSE),
        ]
 
        response = self.client.get(
            reverse('find_kroger_stores'),
            {'lat': 38.9099, 'lon': -104.7266, 'ingredient': 'saffron'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        for store in data['stores']:
            self.assertIn('name', store)
            self.assertIn('address', store)
            self.assertIn('distance', store)
 
    @patch('home.kroger.urllib.request.urlopen')
    def test_returns_empty_list_when_no_stores_found(self, mock_urlopen):
        """Tests that a 200 with an empty list is returned when Kroger finds no nearby stores"""
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_TOKEN_RESPONSE),
            make_mock_response(MOCK_KROGER_EMPTY_RESPONSE),
        ]
 
        response = self.client.get(
            reverse('find_kroger_stores'),
            {'lat': 71.2906, 'lon': -156.7887, 'ingredient': 'saffron'}  # remote location
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('stores', data)
        self.assertEqual(data['stores'], [])
 
    @patch('home.kroger.urllib.request.urlopen')
    def test_returns_502_on_kroger_network_error(self, mock_urlopen):
        """Tests that a Kroger API network failure returns a 502 error"""
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
 
        response = self.client.get(
            reverse('find_kroger_stores'),
            {'lat': 38.9099, 'lon': -104.7266, 'ingredient': 'saffron'}
        )
        self.assertEqual(response.status_code, 502)
        data = json.loads(response.content)
        self.assertIn('error', data)
 
    @patch('home.kroger.urllib.request.urlopen')
    def test_kroger_api_is_called_with_lat_and_lon(self, mock_urlopen):
        """Tests that the Kroger locations request includes the lat/lon params"""
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_TOKEN_RESPONSE),
            make_mock_response(MOCK_KROGER_STORE_RESPONSE),
        ]
 
        self.client.get(
            reverse('find_kroger_stores'),
            {'lat': 38.9099, 'lon': -104.7266, 'ingredient': 'saffron'}
        )
        self.assertEqual(mock_urlopen.call_count, 2)
        # Second call is the locations request — check its URL contains the coordinates
        locations_request = mock_urlopen.call_args_list[1][0][0]
        call_url = locations_request.full_url
        self.assertIn('38.9099', call_url)
        self.assertIn('-104.7266', call_url)
 
    @patch('home.kroger.urllib.request.urlopen')
    def test_two_api_calls_are_made(self, mock_urlopen):
        """Tests that the store finder makes exactly two urlopen calls: token + locations"""
        cache.clear()
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_TOKEN_RESPONSE),
            make_mock_response(MOCK_KROGER_STORE_RESPONSE),
        ]
 
        self.client.get(
            reverse('find_kroger_stores'),
            {'lat': 38.9099, 'lon': -104.7266, 'ingredient': 'saffron'}
        )
        self.assertEqual(mock_urlopen.call_count, 2)
 
    @patch('home.kroger.urllib.request.urlopen')
    def test_token_is_cached_between_requests(self, mock_urlopen):
        """Tests that a cached token avoids a second token fetch on repeat requests"""
        cache.clear()
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_TOKEN_RESPONSE),   # token fetch
            make_mock_response(MOCK_KROGER_STORE_RESPONSE),  # first locations call
            make_mock_response(MOCK_KROGER_STORE_RESPONSE),  # second locations call (no token call)
        ]
 
        self.client.get(
            reverse('find_kroger_stores'),
            {'lat': 38.9099, 'lon': -104.7266, 'ingredient': 'saffron'}
        )
        self.client.get(
            reverse('find_kroger_stores'),
            {'lat': 38.9099, 'lon': -104.7266, 'ingredient': 'garlic'}
        )
        # Only 3 total calls — token fetched once, locations fetched twice
        self.assertEqual(mock_urlopen.call_count, 3)
 
    def test_recipe_page_serves_ingredients_as_objects_with_display_and_name(self):

        response = self.client.get(reverse('recipe_view', args=[self.recipe.id]))
        self.assertEqual(response.status_code, 200)
 
        # Confirm the ingredients JSON is in the page and has the correct shape
        ingredients = response.context['ingredients_json']
        self.assertTrue(len(ingredients) > 0)
        for ing in ingredients:
            self.assertIn('display', ing, "Each ingredient must have a 'display' field for voice.js")
            self.assertIn('name', ing,    "Each ingredient must have a 'name' field for pantry matching")
 
    def test_recipe_page_serves_pantry_names_for_js_matching(self):
        # Add saffron to the pantry so it appears in pantry_names_json
        self.user.pantry_items.create(ingredient_name='saffron')
 
        response = self.client.get(reverse('recipe_view', args=[self.recipe.id]))
        self.assertEqual(response.status_code, 200)
 
        pantry_names = response.context['pantry_names_json']
        self.assertIn('saffron', pantry_names)
 
    def test_recipe_page_pantry_names_are_lowercase(self):
        self.user.pantry_items.create(ingredient_name='Saffron')  # stored with capital S
 
        response = self.client.get(reverse('recipe_view', args=[self.recipe.id]))
        pantry_names = response.context['pantry_names_json']
 
        self.assertIn('saffron', pantry_names)
        self.assertNotIn('Saffron', pantry_names)
 
#### end Kroger store finder tests ####
 