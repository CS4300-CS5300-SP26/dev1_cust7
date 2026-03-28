import json
from io import BytesIO
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from home.models import Pantry
from home.models import Recipe, RecipeIngredient


# https://docs.djangoproject.com/en/6.0/topics/testing/overview/ Reference as needed
# Model tests need to be made

# API tests are being made
class TestAPI(APITestCase):
    def test_index_page_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

#### Spoonacular nutrition label tests ####
#### Mock found with Claud ####
#Sample data that mimics a real Spoonaclur ingredient search response
MOCK_SEARCH_RESPONSE = {
    "results": [{"id": 9040, "name": "banana"}],
    "offset": 0, "number": 1, "totalResults": 1,
}

# Sample data that mimics a real Spoonacular nutrition response
MOCK_NUTRITION_RESPONSE = {
    "id": 9040,
    "name": "banana",
    "nutrition": {
        "nutrients": [
            {"name": "Calories",      "amount": 89.0,  "unit": "kcal", "percentOfDailyNeeds": 4.45},
            {"name": "Fat",           "amount": 0.33,  "unit": "g",    "percentOfDailyNeeds": 0.51},
            {"name": "Saturated Fat", "amount": 0.11,  "unit": "g",    "percentOfDailyNeeds": 0.69},
            {"name": "Carbohydrates", "amount": 22.84, "unit": "g",    "percentOfDailyNeeds": 7.61},
            {"name": "Fiber",         "amount": 2.6,   "unit": "g",    "percentOfDailyNeeds": 10.4},
            {"name": "Sugar",         "amount": 12.23, "unit": "g",    "percentOfDailyNeeds": 13.59},
            {"name": "Protein",       "amount": 1.09,  "unit": "g",    "percentOfDailyNeeds": 2.18},
            {"name": "Sodium",        "amount": 1.0,   "unit": "mg",   "percentOfDailyNeeds": 0.04},
            {"name": "Potassium",     "amount": 358.0, "unit": "mg",   "percentOfDailyNeeds": 10.23},
            {"name": "Vitamin C",     "amount": 8.7,   "unit": "mg",   "percentOfDailyNeeds": 9.67},
        ],
        "weightPerServing": {"amount": 100, "unit": "g"},
    },
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


class NutritionViewTests(TestCase):

    #Create a test client to make requests without running server
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        self.client.login(username='testuser', password='password123')
    
    def test_pantry_view_status(self):
        """Tests that the pantry page loads for a logged-in user"""
        response = self.client.get(reverse('pantry'))
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('index'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_add_ingredient_success(self):
        """Tests adding an ingredient via AJAX"""
        data = {'ingredient_name': 'Carrot'}
        response = self.client.post(
            reverse('add_ingredient'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Pantry.objects.filter(ingredient_name='Carrot').exists())

    def test_add_duplicate_ingredient(self):
        """Tests that duplicate ingredients are rejected (covers error lines)"""
        Pantry.objects.create(user=self.user, ingredient_name='Apple')
        data = {'ingredient_name': 'Apple'}
        response = self.client.post(
            reverse('add_ingredient'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400) # Covers the 'exists()' check logic

    def test_delete_ingredient(self):
        """Tests removing an ingredient"""
        item = Pantry.objects.create(user=self.user, ingredient_name='Onion')
        response = self.client.post(reverse('delete_ingredient', args=[item.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Pantry.objects.filter(id=item.id).exists())

    def test_search_recipes_empty_pantry(self):
        """Tests recipe search logic when pantry is empty (covers early return lines)"""
        response = self.client.get(reverse('search_recipes_by_pantry'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('No ingredients in pantry', response.json().get('message', ''))
    
    @patch('urllib.request.urlopen')
    def test_search_recipes_with_ingredients_success(self, mock_urlopen):
        """Tests recipe search with ingredients (Mocking Spoonacular)"""
        # Add an ingredient so the search logic actually runs
        Pantry.objects.create(user=self.user, ingredient_name='Chicken')
        
        # Mock a successful Spoonacular recipe list
        mock_recipes = [{"id": 1, "title": "Chicken Soup", "image": "img.jpg", 
                         "usedIngredients": [{"name": "chicken"}], "missedIngredients": []}]
        mock_urlopen.return_value = make_mock_response(mock_recipes)
        
        response = self.client.get(reverse('search_recipes_by_pantry'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['recipes']), 1)

    def test_get_fallback_recipes_logic(self):
        """Tests the fallback logic when no API is called"""
        from home.views import get_fallback_recipes
        # Directly test the helper function to cover those 244-324 lines
        pantry_items = ['Potato']
        recipes = get_fallback_recipes(pantry_items)
        self.assertTrue(len(recipes) > 0)

    @patch('urllib.request.urlopen')
    def test_returns_nutrition_data_for_valid_ingredient(self, mock_urlopen):
        #simulate the ingredient search call and the nutrition lookup call
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_SEARCH_RESPONSE),
            make_mock_response(MOCK_NUTRITION_RESPONSE),
        ]
        #Check if view returns 200 and nutrition data
        response = self.client.get(reverse('get_nutrition', args=['banana']))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['name'], 'banana')
        self.assertIn('nutrition', data)

    @patch('urllib.request.urlopen')
    def test_returns_404_when_ingredient_not_found(self, mock_urlopen):
        #Simulate spoonacular returning an empty results list
        mock_urlopen.return_value = make_mock_response({"results": [], "totalResults": 0})
        response = self.client.get(reverse('get_nutrition', args=['xyzunknown']))
        # View should return 404 with an error message
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)

    @patch('urllib.request.urlopen')
    def test_returns_502_on_network_error(self, mock_urlopen):
        #Raise URLerror to simulate network failure
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        response = self.client.get(reverse('get_nutrition', args=['banana']))
        #View should return 502
        self.assertEqual(response.status_code, 502)
        data = json.loads(response.content)
        self.assertIn('error', data)

    @patch('urllib.request.urlopen')
    def test_two_api_calls_are_made(self, mock_urlopen):
        #check if view makes 2 calls to urlopen
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_SEARCH_RESPONSE),
            make_mock_response(MOCK_NUTRITION_RESPONSE),
        ]
        self.client.get(reverse('get_nutrition', args=['banana']))
        self.assertEqual(mock_urlopen.call_count, 2)
####end spoonacular nutrition label tests####

#### Recipe Model Tests ####
class RecipeModelTests(TestCase):
 
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
 
    def test_recipe_is_created_with_required_fields(self):
        """Given a recipe is created, it includes a title and instructions"""
        recipe = Recipe.objects.create(
            user=self.user,
            title='Banana Pancakes',
            instructions='Mix and fry.'
        )
        self.assertEqual(recipe.title, 'Banana Pancakes')
        self.assertEqual(recipe.instructions, 'Mix and fry.')
 
    def test_recipe_is_assigned_unique_id_on_save(self):
        """Given a recipe is stored, it is assigned a unique identifier"""
        recipe1 = Recipe.objects.create(user=self.user, title='Soup', instructions='Boil.')
        recipe2 = Recipe.objects.create(user=self.user, title='Salad', instructions='Toss.')
        self.assertIsNotNone(recipe1.id)
        self.assertIsNotNone(recipe2.id)
        self.assertNotEqual(recipe1.id, recipe2.id)
 
    def test_recipe_can_be_retrieved_by_id(self):
        """Given a recipe is saved, it can be retrieved from the system using its ID"""
        recipe = Recipe.objects.create(
            user=self.user,
            title='Omelette',
            instructions='Whisk eggs and cook.'
        )
        retrieved = Recipe.objects.get(id=recipe.id)
        self.assertEqual(retrieved.title, 'Omelette')
 
    def test_recipe_ingredient_contains_name_quantity_and_unit(self):
        """Given a recipe includes ingredients, each ingredient has a name, quantity, and unit"""
        recipe = Recipe.objects.create(user=self.user, title='Pasta', instructions='Boil pasta.')
        ingredient = RecipeIngredient.objects.create(
            recipe=recipe,
            name='Pasta',
            quantity='200',
            unit='g'
        )
        self.assertEqual(ingredient.name, 'Pasta')
        self.assertEqual(ingredient.quantity, '200')
        self.assertEqual(ingredient.unit, 'g')
 
    def test_recipe_ingredient_unit_is_optional(self):
        """Given an ingredient is created, unit is not required"""
        recipe = Recipe.objects.create(user=self.user, title='Boiled Egg', instructions='Boil egg.')
        ingredient = RecipeIngredient.objects.create(
            recipe=recipe,
            name='Egg',
            quantity='2'
        )
        self.assertIsNone(ingredient.unit)
 
    def test_recipe_requires_title(self):
        """Given title is missing, the system prevents the recipe from being saved"""
        recipe = Recipe(user=self.user, title='', instructions='Some instructions.')
        with self.assertRaises(ValidationError):
            recipe.full_clean()
 
    def test_recipe_requires_instructions(self):
        """Given instructions are missing, the system prevents the recipe from being saved"""
        recipe = Recipe(user=self.user, title='Some Title', instructions='')
        with self.assertRaises(ValidationError):
            recipe.full_clean()
 
    def test_recipe_ingredient_requires_name(self):
        """Given ingredient name is missing, the system prevents it from being saved"""
        recipe = Recipe.objects.create(user=self.user, title='Stew', instructions='Cook slowly.')
        ingredient = RecipeIngredient(recipe=recipe, name='', quantity='100', unit='g')
        with self.assertRaises(ValidationError):
            ingredient.full_clean()
 
    def test_recipe_ingredient_requires_quantity(self):
        """Given ingredient quantity is missing, the system prevents it from being saved"""
        recipe = Recipe.objects.create(user=self.user, title='Stew', instructions='Cook slowly.')
        ingredient = RecipeIngredient(recipe=recipe, name='Carrot', quantity='', unit='g')
        with self.assertRaises(ValidationError):
            ingredient.full_clean()
 
    def test_recipe_str(self):
        """Tests the string representation of a recipe"""
        recipe = Recipe.objects.create(user=self.user, title='Waffles', instructions='Mix and cook.')
        self.assertEqual(str(recipe), 'testuser - Waffles')
 
    def test_recipe_ingredient_str(self):
        """Tests the string representation of a recipe ingredient"""
        recipe = Recipe.objects.create(user=self.user, title='Waffles', instructions='Mix and cook.')
        ingredient = RecipeIngredient.objects.create(recipe=recipe, name='Flour', quantity='100', unit='g')
        self.assertEqual(str(ingredient), 'Waffles - Flour')
 
    def test_recipe_ingredients_deleted_when_recipe_deleted(self):
        """Tests that ingredients are cascade deleted with the recipe"""
        recipe = Recipe.objects.create(user=self.user, title='Toast', instructions='Toast bread.')
        RecipeIngredient.objects.create(recipe=recipe, name='Bread', quantity='2')
        recipe_id = recipe.id
        recipe.delete()
        self.assertFalse(RecipeIngredient.objects.filter(recipe_id=recipe_id).exists())
 #### End recipe model tests ####
 
 