import json
from io import BytesIO
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from home.models import Pantry, Recipe, RecipeIngredient, RecipeRating, RecipeStep
from django.core.cache import cache

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
        cache.clear()
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
    
    @patch('home.spoonacular.urllib.request.urlopen')
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

    @patch('home.spoonacular.urllib.request.urlopen')
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

    @patch('home.spoonacular.urllib.request.urlopen')
    def test_returns_404_when_ingredient_not_found(self, mock_urlopen):
        #Simulate spoonacular returning an empty results list
        mock_urlopen.return_value = make_mock_response({"results": [], "totalResults": 0})
        response = self.client.get(reverse('get_nutrition', args=['xyzunknown']))
        # View should return 404 with an error message
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)

    @patch('home.spoonacular.urllib.request.urlopen')
    def test_returns_502_on_network_error(self, mock_urlopen):
        #Raise URLerror to simulate network failure
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        response = self.client.get(reverse('get_nutrition', args=['banana']))
        #View should return 502
        self.assertEqual(response.status_code, 502)
        data = json.loads(response.content)
        self.assertIn('error', data)

    @patch('home.spoonacular.urllib.request.urlopen')
    def test_two_api_calls_are_made(self, mock_urlopen):
        cache.clear()
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
        """Given a recipe is created, it includes a title"""
        recipe = Recipe.objects.create(user=self.user, title='Banana Pancakes')
        self.assertEqual(recipe.title, 'Banana Pancakes')
 
    def test_recipe_is_assigned_unique_id_on_save(self):
        """Given a recipe is stored, it is assigned a unique identifier"""
        recipe1 = Recipe.objects.create(user=self.user, title='Soup')
        recipe2 = Recipe.objects.create(user=self.user, title='Salad')
        self.assertIsNotNone(recipe1.id)
        self.assertIsNotNone(recipe2.id)
        self.assertNotEqual(recipe1.id, recipe2.id)
 
    def test_recipe_can_be_retrieved_by_id(self):
        """Given a recipe is saved, it can be retrieved from the system using its ID"""
        recipe = Recipe.objects.create(user=self.user, title='Omelette')
        retrieved = Recipe.objects.get(id=recipe.id)
        self.assertEqual(retrieved.title, 'Omelette')
 
    def test_recipe_requires_title(self):
        """Given title is missing, the system prevents the recipe from being saved"""
        recipe = Recipe(user=self.user, title='')
        with self.assertRaises(ValidationError):
            recipe.full_clean()
 
    def test_recipe_str(self):
        """Tests the string representation of a recipe"""
        recipe = Recipe.objects.create(user=self.user, title='Waffles')
        self.assertEqual(str(recipe), 'testuser - Waffles')
 
    # ---- Step tests ----
 
    def test_step_is_created_with_order_and_text(self):
        """Given a step is created, it has an order and text"""
        recipe = Recipe.objects.create(user=self.user, title='Pasta')
        step = RecipeStep.objects.create(recipe=recipe, order=1, text='Boil water.')
        self.assertEqual(step.order, 1)
        self.assertEqual(step.text, 'Boil water.')
 
    def test_steps_are_returned_in_order(self):
        """Given multiple steps exist, they are returned in ascending order"""
        recipe = Recipe.objects.create(user=self.user, title='Pasta')
        RecipeStep.objects.create(recipe=recipe, order=3, text='Drain and serve.')
        RecipeStep.objects.create(recipe=recipe, order=1, text='Boil water.')
        RecipeStep.objects.create(recipe=recipe, order=2, text='Add pasta.')
        steps = list(recipe.steps.all())
        self.assertEqual(steps[0].order, 1)
        self.assertEqual(steps[1].order, 2)
        self.assertEqual(steps[2].order, 3)
 
    def test_steps_deleted_when_recipe_deleted(self):
        """Given a recipe is deleted, all its steps are also deleted"""
        recipe = Recipe.objects.create(user=self.user, title='Toast')
        RecipeStep.objects.create(recipe=recipe, order=1, text='Toast bread.')
        recipe_id = recipe.id
        recipe.delete()
        self.assertFalse(RecipeStep.objects.filter(recipe_id=recipe_id).exists())
 
    def test_step_requires_text(self):
        """Given step text is missing, the system prevents it from being saved"""
        recipe = Recipe.objects.create(user=self.user, title='Stew')
        step = RecipeStep(recipe=recipe, order=1, text='')
        with self.assertRaises(ValidationError):
            step.full_clean()
 
    def test_step_requires_order(self):
        """Given step order is missing, the system prevents it from being saved"""
        recipe = Recipe.objects.create(user=self.user, title='Stew')
        step = RecipeStep(recipe=recipe, order=None, text='Cook slowly.')
        with self.assertRaises(ValidationError):
            step.full_clean()
 
    def test_recipe_can_have_multiple_steps(self):
        """Given a recipe has multiple steps, all are retrievable"""
        recipe = Recipe.objects.create(user=self.user, title='Omelette')
        RecipeStep.objects.create(recipe=recipe, order=1, text='Crack eggs.')
        RecipeStep.objects.create(recipe=recipe, order=2, text='Whisk.')
        RecipeStep.objects.create(recipe=recipe, order=3, text='Cook in pan.')
        self.assertEqual(recipe.steps.count(), 3)
 
    def test_step_str(self):
        """Tests the string representation of a recipe step"""
        recipe = Recipe.objects.create(user=self.user, title='Waffles')
        step = RecipeStep.objects.create(recipe=recipe, order=1, text='Mix batter.')
        self.assertEqual(str(step), 'Waffles - Step 1')
 
    # ---- Ingredient tests ----
 
    def test_recipe_ingredient_contains_name_quantity_and_unit(self):
        """Given a recipe includes ingredients, each ingredient has a name, quantity, and unit"""
        recipe = Recipe.objects.create(user=self.user, title='Pasta')
        ingredient = RecipeIngredient.objects.create(recipe=recipe, name='Pasta', quantity='200', unit='g')
        self.assertEqual(ingredient.name, 'Pasta')
        self.assertEqual(ingredient.quantity, '200')
        self.assertEqual(ingredient.unit, 'g')
 
    def test_recipe_ingredient_unit_is_optional(self):
        """Given an ingredient is created, unit is not required"""
        recipe = Recipe.objects.create(user=self.user, title='Boiled Egg')
        ingredient = RecipeIngredient.objects.create(recipe=recipe, name='Egg', quantity='2')
        self.assertIsNone(ingredient.unit)
 
    def test_recipe_ingredient_requires_name(self):
        """Given ingredient name is missing, the system prevents it from being saved"""
        recipe = Recipe.objects.create(user=self.user, title='Stew')
        ingredient = RecipeIngredient(recipe=recipe, name='', quantity='100', unit='g')
        with self.assertRaises(ValidationError):
            ingredient.full_clean()
 
    def test_recipe_ingredient_requires_quantity(self):
        """Given ingredient quantity is missing, the system prevents it from being saved"""
        recipe = Recipe.objects.create(user=self.user, title='Stew')
        ingredient = RecipeIngredient(recipe=recipe, name='Carrot', quantity='', unit='g')
        with self.assertRaises(ValidationError):
            ingredient.full_clean()
 
    def test_recipe_ingredient_str(self):
        """Tests the string representation of a recipe ingredient"""
        recipe = Recipe.objects.create(user=self.user, title='Waffles')
        ingredient = RecipeIngredient.objects.create(recipe=recipe, name='Flour', quantity='100', unit='g')
        self.assertEqual(str(ingredient), 'Waffles - Flour')
 
    def test_recipe_ingredients_deleted_when_recipe_deleted(self):
        """Tests that ingredients are cascade deleted with the recipe"""
        recipe = Recipe.objects.create(user=self.user, title='Toast')
        RecipeIngredient.objects.create(recipe=recipe, name='Bread', quantity='2')
        recipe_id = recipe.id
        recipe.delete()
        self.assertFalse(RecipeIngredient.objects.filter(recipe_id=recipe_id).exists())
 
    # ---- Visibility tests ----
 
    def test_recipe_defaults_to_private(self):
        """Given a recipe is created without specifying visibility, it defaults to private"""
        recipe = Recipe.objects.create(user=self.user, title='Secret Soup')
        self.assertFalse(recipe.is_public)
 
    def test_recipe_can_be_set_to_public(self):
        """Given a recipe is created with is_public=True, it is marked as public"""
        recipe = Recipe.objects.create(user=self.user, title='Famous Cake', is_public=True)
        self.assertTrue(recipe.is_public)
 
    def test_recipe_visibility_can_be_toggled(self):
        """Given a private recipe, it can be updated to public and back"""
        recipe = Recipe.objects.create(user=self.user, title='Toggleable Stew')
        self.assertFalse(recipe.is_public)
        recipe.is_public = True
        recipe.save()
        self.assertTrue(Recipe.objects.get(id=recipe.id).is_public)
        recipe.is_public = False
        recipe.save()
        self.assertFalse(Recipe.objects.get(id=recipe.id).is_public)
 
    # ---- Rating tests ----
 
    def test_average_rating_returns_none_when_no_ratings(self):
        """Given a recipe has no ratings, average_rating returns None"""
        recipe = Recipe.objects.create(user=self.user, title='Unrated Dish')
        self.assertIsNone(recipe.average_rating())
 
    def test_average_rating_with_single_rating(self):
        """Given a recipe has one rating, average_rating returns that value"""
        recipe = Recipe.objects.create(user=self.user, title='Solo Rated')
        RecipeRating.objects.create(recipe=recipe, user=self.user, stars=4)
        self.assertEqual(recipe.average_rating(), 4)
 
    def test_average_rating_with_multiple_ratings(self):
        """Given a recipe has multiple ratings, average_rating returns the correct average"""
        recipe = Recipe.objects.create(user=self.user, title='Multi Rated')
        user2 = User.objects.create_user(username='user2', password='password123')
        user3 = User.objects.create_user(username='user3', password='password123')
        RecipeRating.objects.create(recipe=recipe, user=self.user, stars=5)
        RecipeRating.objects.create(recipe=recipe, user=user2, stars=3)
        RecipeRating.objects.create(recipe=recipe, user=user3, stars=4)
        self.assertAlmostEqual(recipe.average_rating(), 4.0)
 
    def test_rating_rejects_invalid_star_values(self):
        """Given a rating outside 1-5 is submitted, the system rejects it"""
        recipe = Recipe.objects.create(user=self.user, title='Bad Rating')
        for invalid in [0, 6, -1]:
            rating = RecipeRating(recipe=recipe, user=self.user, stars=invalid)
            with self.assertRaises(ValidationError):
                rating.full_clean()
 
    def test_user_cannot_rate_same_recipe_twice(self):
        """Given a user has already rated a recipe, a second rating is rejected"""
        recipe = Recipe.objects.create(user=self.user, title='Double Rated')
        RecipeRating.objects.create(recipe=recipe, user=self.user, stars=3)
        with self.assertRaises(Exception):
            RecipeRating.objects.create(recipe=recipe, user=self.user, stars=5)
 
    def test_ratings_deleted_when_recipe_deleted(self):
        """Given a recipe is deleted, all its ratings are also deleted"""
        recipe = Recipe.objects.create(user=self.user, title='Doomed Recipe')
        RecipeRating.objects.create(recipe=recipe, user=self.user, stars=5)
        recipe_id = recipe.id
        recipe.delete()
        self.assertFalse(RecipeRating.objects.filter(recipe_id=recipe_id).exists())
 
    def test_recipe_rating_str(self):
        """Tests the string representation of a recipe rating"""
        recipe = Recipe.objects.create(user=self.user, title='Tacos')
        rating = RecipeRating.objects.create(recipe=recipe, user=self.user, stars=5)
        self.assertEqual(str(rating), 'testuser - Tacos - 5 stars')
 
 #### End recipe model tests ####

#### Missing Code Coverage Tests (Error Handling, API Failures, Edge Cases) ####
class MissingCoverageTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    @patch('home.spoonacular._get_next_key')
    def test_spoonacular_all_keys_exhausted(self, mock_get_key):
        """Test spoonacular.py line 23: All API keys exhausted scenario"""
        mock_get_key.return_value = None  # No keys available
        from home.spoonacular import spoonacular_get
        with self.assertRaises(Exception) as context:
            spoonacular_get("food/ingredients/search", {"query": "test"})
        self.assertIn("All Spoonacular API keys are exhausted", str(context.exception))

    @patch('home.spoonacular.cache.get')
    def test_spoonacular_cache_hit(self, mock_cache_get):
        """Test spoonacular.py line 31: Cache hit returns cached data without API call"""
        cached_data = {"results": [{"id": 1, "name": "cached"}]}
        mock_cache_get.return_value = cached_data
        from home.spoonacular import spoonacular_get
        
        with patch('home.spoonacular.urllib.request.urlopen') as mock_urlopen:
            result = spoonacular_get("food/ingredients/search", {"query": "test"})
            self.assertEqual(result, cached_data)
            mock_urlopen.assert_not_called()  # Should not make API call

    @patch('home.views.spoonacular_get')
    def test_get_nutrition_api_search_failure(self, mock_spoonacular):
        """Test views.py lines 41-45: API search failure in get_nutrition"""
        mock_spoonacular.side_effect = Exception("API timeout")
        response = self.client.get(reverse('get_nutrition', args=['banana']))
        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertIn("Search request failed", data['error'])

    @patch('home.views.spoonacular_get')
    def test_get_nutrition_no_ingredient_found(self, mock_spoonacular):
        """Test views.py line 51: No ingredient found in search results"""
        mock_spoonacular.return_value = {"results": []}
        response = self.client.get(reverse('get_nutrition', args=['xyzunknown']))
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("No ingredient found matching", data['error'])

    @patch('home.views.spoonacular_get')
    def test_get_nutrition_nutrition_api_failure(self, mock_spoonacular):
        """Test views.py lines 56-57: Nutrition API failure"""
        mock_spoonacular.side_effect = [
            {"results": [{"id": 1, "name": "banana"}]},  # Search succeeds
            Exception("Nutrition API down")  # Nutrition lookup fails
        ]
        response = self.client.get(reverse('get_nutrition', args=['banana']))
        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertIn("Nutrition request failed", data['error'])

    def test_register_form_validation_errors(self):
        """Test views.py lines 72-82: Form validation errors in register view"""
        with patch('home.views.print') as mock_print:
            response = self.client.post(reverse('register'), {
                'username': 'testuser',  # Already exists
                'password1': 'password123',
                'password2': 'password123'
            })
            # Should render form with errors, not redirect
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'form')
            mock_print.assert_called()  # Form errors should be printed

    def test_signin_invalid_credentials(self):
        """Test views.py line 103: Invalid username/password in signin"""
        response = self.client.post(reverse('signin'), {
            'username': 'nonexistent',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

    def test_add_ingredient_json_parse_error(self):
        """Test views.py lines 120-165: JSON parsing error in add_ingredient"""
        self.client.login(username='testuser', password='password123')
        response = self.client.post(
            reverse('add_ingredient'),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)

    def test_add_ingredient_empty_name(self):
        """Test views.py lines 120-165: Empty ingredient name validation"""
        self.client.login(username='testuser', password='password123')
        response = self.client.post(
            reverse('add_ingredient'),
            data=json.dumps({'ingredient_name': ''}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'Ingredient name is required')

    def test_add_ingredient_duplicate(self):
        """Test views.py lines 120-165: Duplicate ingredient prevention"""
        self.client.login(username='testuser', password='password123')
        # Add ingredient first time
        response1 = self.client.post(
            reverse('add_ingredient'),
            data=json.dumps({'ingredient_name': 'Apple'}),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, 200)
        
        # Try to add same ingredient again
        response2 = self.client.post(
            reverse('add_ingredient'),
            data=json.dumps({'ingredient_name': 'Apple'}),
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, 400)
        data = response2.json()
        self.assertEqual(data['error'], 'Ingredient already in pantry')

    def test_delete_ingredient_not_found(self):
        """Test views.py lines 120-165: Deleting non-existent ingredient"""
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('delete_ingredient', args=[999]))
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)

    @patch('home.spoonacular._get_next_key')
    def test_search_recipes_all_keys_exhausted(self, mock_get_key):
        """Test spoonacular.py line 23: All API keys exhausted raises exception in recipe search"""
        mock_get_key.return_value = None
        self.client.login(username='testuser', password='password123')
        Pantry.objects.create(user=self.user, ingredient_name='Chicken')
        response = self.client.get(reverse('search_recipes_by_pantry'))
        # When all keys are exhausted, an exception is raised resulting in 502
        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertIn('error', data)

    def test_get_fallback_recipes_no_matches(self):
        """Test views.py lines 207-215: Fallback recipes when no ingredients match"""
        pantry_items = ['xyzunknown']  # No matching recipes
        from home.views import get_fallback_recipes
        fallback = get_fallback_recipes(pantry_items)
        self.assertEqual(len(fallback), 1)
        self.assertEqual(fallback[0]['title'], 'Basic Recipe Suggestions')
        self.assertEqual(fallback[0]['used_ingredient_count'], 0)

    def test_pantry_str_edge_case(self):
        """Test models.py line 17: Pantry.__str__ with edge case"""
        pantry = Pantry.objects.create(user=self.user, ingredient_name='Test Ingredient')
        expected = f"{self.user.username} - Test Ingredient"
        self.assertEqual(str(pantry), expected)
#### End Missing Coverage Tests ####
 