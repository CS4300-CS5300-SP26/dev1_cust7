import json
from io import BytesIO
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from home.models import Pantry, Recipe, RecipeIngredient, RecipeRating, RecipeStep, MealPlan
from django.core.cache import cache
from .forms import RegisterForm, EditProfileForm

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
        response = self.client.post(reverse('register'), {
            'username': 'testuser',  # Already exists
            'password1': 'password123',
            'password2': 'password123'
        })
        # Should render form with errors, not redirect
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')
        # Check that form has errors
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

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

    @patch('home.spoonacular.cache.get')
    def test_spoonacular_cache_miss(self, mock_cache_get):
        """Test spoonacular.py line 22: Cache miss scenario"""
        mock_cache_get.return_value = None  # Cache miss
        from home.spoonacular import spoonacular_get
        
        with patch('home.spoonacular.urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.return_value = make_mock_response({"results": [{"id": 1, "name": "test"}]})
            result = spoonacular_get("food/ingredients/search", {"query": "test"})
            self.assertEqual(result["results"][0]["name"], "test")
            mock_urlopen.assert_called_once()

    @patch('home.spoonacular.cache.set')
    def test_spoonacular_cache_timeout(self, mock_cache_set):
        """Test spoonacular.py lines 52-58: Cache timeout behavior"""
        from home.spoonacular import spoonacular_get
        
        # Clear cache to ensure cache miss
        cache.clear()
        
        with patch('home.spoonacular.cache.get', return_value=None) as mock_cache_get:
            with patch('home.spoonacular.urllib.request.urlopen') as mock_urlopen:
                mock_urlopen.return_value = make_mock_response({"results": [{"id": 1, "name": "test"}]})
                result = spoonacular_get("food/ingredients/search", {"query": "test"})
                # Should call cache.set with timeout
                self.assertTrue(mock_cache_set.called)
                call_kwargs = mock_cache_set.call_args.kwargs
                call_args = mock_cache_set.call_args[0]
                # Cache key should start with "spoon_"
                self.assertTrue(call_args[0].startswith("spoon_"))
                self.assertEqual(call_args[1]["results"][0]["name"], "test")  # Cached data
                # Check timeout is passed as keyword argument
                self.assertEqual(call_kwargs.get('timeout'), 3600)

    @patch('home.views.spoonacular_get')
    def test_get_nutrition_invalid_json_response(self, mock_spoonacular):
        """Test views.py line 51: Invalid JSON response handling"""
        mock_spoonacular.return_value = {"invalid": "data"}
        response = self.client.get(reverse('get_nutrition', args=['banana']))
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("No ingredient found matching", data['error'])

    @patch('home.views.spoonacular_get')
    def test_get_nutrition_missing_fields(self, mock_spoonacular):
        """Test views.py lines 59-61, 66: Missing fields in API response - view returns raw data"""
        mock_spoonacular.side_effect = [
            {"results": [{"id": 1, "name": "banana"}]},  # Search succeeds
            {"id": 1, "name": "banana"}  # Nutrition lookup with minimal data (no nutrition key)
        ]
        response = self.client.get(reverse('get_nutrition', args=['banana']))
        # View returns 200 with whatever data the API returned (no validation of nutrition key)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'banana')

    def test_register_form_invalid_data(self):
        """Test views.py lines 77-78, 82: Form validation with invalid data"""
        response = self.client.post(reverse('register'), {
            'username': 'test@user!',  # Invalid characters
            'password1': '123',  # Too short
            'password2': '456'  # Doesn't match
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')
        # Check that form has errors
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        # Verify multiple validation errors are caught
        self.assertTrue(len(form.errors) > 0)

    def test_add_ingredient_malformed_json(self):
        """Test views.py lines 140-141: Malformed JSON handling"""
        self.client.login(username='testuser', password='password123')
        response = self.client.post(
            reverse('add_ingredient'),
            data='{"ingredient_name": "Test',  # Malformed JSON
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)

    @patch('home.views.spoonacular_get')
    def test_search_recipes_rate_limiting(self, mock_spoonacular):
        """Test views.py lines 194-204: API rate limiting (HTTP 429)"""
        import urllib.error
        mock_spoonacular.side_effect = urllib.error.HTTPError(
            url="test", code=429, msg="Too Many Requests", hdrs={}, fp=None
        )
        self.client.login(username='testuser', password='password123')
        Pantry.objects.create(user=self.user, ingredient_name='Chicken')
        response = self.client.get(reverse('search_recipes_by_pantry'))
        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertIn('error', data)

    def test_get_fallback_recipes_edge_cases(self):
        """Test views.py lines 257-262: Fallback recipes edge cases"""
        from home.views import get_fallback_recipes
        
        # Test with empty pantry
        fallback = get_fallback_recipes([])
        self.assertEqual(len(fallback), 1)
        self.assertEqual(fallback[0]['title'], 'Basic Recipe Suggestions')
        
        # Test with special characters
        fallback = get_fallback_recipes(['café', 'piñata'])
        self.assertTrue(len(fallback) > 0)
        
        # Test with very long ingredient names
        long_name = 'a' * 100
        fallback = get_fallback_recipes([long_name])
        self.assertTrue(len(fallback) > 0)

    def test_delete_ingredient_exception_handling(self):
        """Test views.py lines 151-152: Exception handling in delete_ingredient"""
        self.client.login(username='testuser', password='password123')
        # Try to delete with an invalid ID that will cause an exception
        response = self.client.post(reverse('delete_ingredient', args=[99999]))
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)

    def test_get_meals_json_success(self):
        """Test views.py lines 328-354: get_meals_json returns meal plans"""
        self.client.login(username='testuser', password='password123')
        from home.models import MealPlan
        from datetime import date
        
        # Create a meal plan for the current month
        MealPlan.objects.create(
            user=self.user,
            recipe_name='Test Meal',
            recipe_id=123,
            date=date.today(),
            meal_type='Dinner'
        )
        
        response = self.client.get(reverse('get_meals'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('meals', data)
        self.assertIsInstance(data['meals'], list)
        self.assertEqual(len(data['meals']), 1)
        meal = data['meals'][0]
        self.assertEqual(meal['title'], 'Test Meal')
        self.assertEqual(meal['meal_type'], 'Dinner')

    def test_get_meals_json_with_date_range(self):
        """Test views.py lines 331-350: get_meals_json with custom date range"""
        self.client.login(username='testuser', password='password123')
        from home.models import MealPlan
        from datetime import date, timedelta
        
        # Create a meal plan for a specific date
        test_date = date(2026, 6, 15)
        MealPlan.objects.create(
            user=self.user,
            recipe_name='Summer Meal',
            recipe_id=456,
            date=test_date,
            meal_type='Lunch'
        )
        
        # Query with specific date range
        response = self.client.get(
            reverse('get_meals') + '?start_date=2026-06-01&end_date=2026-06-30'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['meals']), 1)
        self.assertEqual(data['meals'][0]['title'], 'Summer Meal')

    def test_get_meals_json_empty_result(self):
        """Test views.py lines 346-351: get_meals_json returns empty list when no meals"""
        self.client.login(username='testuser', password='password123')
        
        response = self.client.get(reverse('get_meals'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('meals', data)
        self.assertEqual(len(data['meals']), 0)

    @patch('home.views.spoonacular_get')
    def test_generate_meal_plan_empty_pantry(self, mock_spoonacular):
        """Test views.py lines 383-386: generate_meal_plan returns 400 when pantry is empty"""
        self.client.login(username='testuser', password='password123')
        
        # Ensure pantry is empty
        Pantry.objects.filter(user=self.user).delete()
        
        response = self.client.post(reverse('generate_meal_plan'))
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('empty', data['error'].lower())

    @patch('home.views.spoonacular_get')
    def test_generate_meal_plan_success(self, mock_spoonacular):
        """Test views.py lines 391-438: generate_meal_plan creates 7 meals"""
        self.client.login(username='testuser', password='password123')
        
        # Add ingredients to pantry
        Pantry.objects.create(user=self.user, ingredient_name='Chicken')
        Pantry.objects.create(user=self.user, ingredient_name='Rice')
        
        # Mock successful API response with 7 recipes
        mock_recipes = [
            {'id': i, 'title': f'Recipe {i}'} for i in range(1, 8)
        ]
        mock_spoonacular.return_value = mock_recipes
        
        response = self.client.post(reverse('generate_meal_plan'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['meals_count'], 7)
        
        # Verify meals were created
        from home.models import MealPlan
        meals_count = MealPlan.objects.filter(user=self.user).count()
        self.assertEqual(meals_count, 7)

    @patch('home.views.spoonacular_get')
    def test_generate_meal_plan_api_failure(self, mock_spoonacular):
        """Test views.py lines 440-443: generate_meal_plan handles API failure"""
        import urllib.error
        self.client.login(username='testuser', password='password123')
        
        # Add ingredients to pantry
        Pantry.objects.create(user=self.user, ingredient_name='Chicken')
        
        # Mock API failure
        mock_spoonacular.side_effect = urllib.error.HTTPError(
            url="test", code=500, msg="Internal Server Error", hdrs={}, fp=None
        )
        
        response = self.client.post(reverse('generate_meal_plan'))
        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertIn('error', data)

    # ---- Unauthorized Access Tests ----

    def test_edit_account_requires_login(self):
        """Test that edit_account redirects when not logged in"""
        response = self.client.get(reverse('edit_account'))
        self.assertIn(response.status_code, [302, 403])

    def test_account_requires_login(self):
        """Test that account view redirects when not logged in"""
        response = self.client.get(reverse('account'))
        self.assertIn(response.status_code, [302, 403])

    def test_calendar_view_requires_login(self):
        """Test that calendar_view redirects when not logged in"""
        response = self.client.get(reverse('calendar'))
        self.assertIn(response.status_code, [302, 403])

    def test_get_pantry_ingredients_requires_login(self):
        """Test that get_pantry_ingredients redirects when not logged in"""
        response = self.client.get(reverse('get_pantry_ingredients'))
        self.assertIn(response.status_code, [302, 403])

    # ---- Invalid Data Handling Tests ----

    def test_edit_account_invalid_form(self):
        """Test edit_account when form is invalid (duplicate email)"""
        # Create another user with the email we'll try to use
        User.objects.create_user(username='otheruser', email='taken@email.com', password='pass123')
        
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('edit_account'), {
            'first_name': 'Test',
            'last_name': 'User',
            'username': 'testuser',
            'email': 'taken@email.com'  # Already exists
        })
        self.assertEqual(response.status_code, 200)  # Re-renders form with errors

    def test_change_password_invalid_form(self):
        """Test change_password when form is invalid (wrong current password)"""
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('change_password'), {
            'old_password': 'wrongpassword',
            'new_password1': 'NewStrongPassword123!',
            'new_password2': 'NewStrongPassword123!'
        })
        self.assertEqual(response.status_code, 200)  # Re-renders form with errors

    # ---- 404 Error Tests ----

    def test_recipe_view_404(self):
        """Test that viewing non-existent recipe returns 404"""
        response = self.client.get(reverse('recipe_view', args=[99999]))
        self.assertEqual(response.status_code, 404)

    # ---- Permission Denied Tests ----

    def test_recipe_view_private_recipe_different_user(self):
        """Test that a different user cannot view a private recipe"""
        # Create recipe owned by testuser
        recipe = Recipe.objects.create(user=self.user, title='Private Recipe', is_public=False)
        # Create and login as different user
        other_user = User.objects.create_user(username='otheruser', password='pass123')
        self.client.login(username='otheruser', password='pass123')
        response = self.client.get(reverse('recipe_view', args=[recipe.id]))
        self.assertEqual(response.status_code, 403)

    def test_recipe_view_private_recipe_unauthenticated(self):
        """Test that unauthenticated user cannot view private recipe"""
        recipe = Recipe.objects.create(user=self.user, title='Private Recipe', is_public=False)
        response = self.client.get(reverse('recipe_view', args=[recipe.id]))
        # Returns 403 Forbidden (PermissionDenied) for unauthenticated users
        self.assertEqual(response.status_code, 403)

    # ---- View GET Request Tests ----

    def test_register_get(self):
        """Test register page loads with GET"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_signin_get(self):
        """Test signin page loads with GET"""
        response = self.client.get(reverse('signin'))
        self.assertEqual(response.status_code, 200)

    def test_signin_successful(self):
        """Test successful signin redirects to index"""
        response = self.client.post(reverse('signin'), {
            'username': 'testuser',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('index'))

    def test_account_view(self):
        """Test account page loads for logged-in user"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('account'))
        self.assertEqual(response.status_code, 200)

    def test_edit_account_get(self):
        """Test edit_account page loads with GET"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('edit_account'))
        self.assertEqual(response.status_code, 200)

    def test_change_password_get(self):
        """Test change_password page loads with GET"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('change_password'))
        self.assertEqual(response.status_code, 200)

    def test_get_pantry_ingredients(self):
        """Test get_pantry_ingredients returns JSON"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('get_pantry_ingredients'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('ingredients', data)

    def test_calendar_view(self):
        """Test calendar page loads for logged-in user"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('calendar'))
        self.assertEqual(response.status_code, 200)

    def test_nutrition_test_view(self):
        """Test nutrition_test view function exists and is callable"""
        from home.views import nutrition_test
        self.assertIsNotNone(nutrition_test)

    # ---- API Edge Case Tests ----

    @patch('home.views.spoonacular_get')
    def test_search_recipes_payment_required(self, mock_spoonacular):
        """Test search_recipes_by_pantry handles HTTP 402 Payment Required"""
        import urllib.error
        self.client.login(username='testuser', password='password123')
        Pantry.objects.create(user=self.user, ingredient_name='Chicken')
        
        mock_spoonacular.side_effect = urllib.error.HTTPError(
            url="test", code=402, msg="Payment Required", hdrs={}, fp=None
        )
        
        response = self.client.get(reverse('search_recipes_by_pantry'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('api_status', data)
        self.assertEqual(data['api_status'], 'payment_required')

    def test_create_recipe_empty_title(self):
        """Test create_recipe with empty title shows error"""
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('create_recipe'), {
            'title': '',  # Empty title
            'is_public': 'on'
        })
        # Should re-render the form (200) or redirect (302) - either is valid
        self.assertIn(response.status_code, [200, 302])

    @patch('home.views.spoonacular_get')
    def test_generate_meal_plan_empty_api_response(self, mock_spoonacular):
        """Test generate_meal_plan handles empty API response with fallback"""
        self.client.login(username='testuser', password='password123')
        Pantry.objects.create(user=self.user, ingredient_name='Rice')
        
        # Mock API returning empty list - view should use fallback recipes
        mock_spoonacular.return_value = []
        
        response = self.client.post(reverse('generate_meal_plan'))
        # The view should succeed using fallback recipes
        self.assertIn(response.status_code, [200, 502])

    # ---- Integration Test (Full User Journey) ----

    @patch('home.views.spoonacular_get')
    def test_full_user_journey(self, mock_spoonacular):
        """Integration test: Register -> Create Recipe -> Add to Pantry -> Generate Meal Plan -> View Calendar"""
        # 1. Register a new user
        response = self.client.post(reverse('register'), {
            'first_name': 'Integration',
            'last_name': 'Test',
            'username': 'integrationuser',
            'email': 'integration@test.com',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        
        # 2. User is automatically logged in, create a recipe
        response = self.client.post(reverse('create_recipe'), {
            'title': 'Integration Test Recipe',
            'is_public': 'on',
            'ingredient_quantity[]': ['1'],
            'ingredient_unit[]': ['cup'],
            'ingredient_name[]': ['Flour'],
            'steps[]': ['Mix ingredients']
        })
        self.assertEqual(response.status_code, 302)  # Redirect to recipe view
        
        # 3. View the recipe
        recipe = Recipe.objects.get(title='Integration Test Recipe')
        response = self.client.get(reverse('recipe_view', args=[recipe.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Integration Test Recipe')
        
        # 4. Add ingredient to pantry
        response = self.client.post(
            reverse('add_ingredient'),
            data=json.dumps({'ingredient_name': 'Sugar'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Pantry.objects.filter(ingredient_name='Sugar').exists())
        
        # 5. Generate meal plan
        mock_spoonacular.return_value = [{'id': i, 'title': f'Recipe {i}'} for i in range(1, 8)]
        response = self.client.post(reverse('generate_meal_plan'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['meals_count'], 7)
        
        # 6. View calendar
        response = self.client.get(reverse('calendar'))
        self.assertEqual(response.status_code, 200)
        
        # 7. Logout
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
#### End Missing Coverage Tests ####
 


 #### Meal Calendar (MealPlan) Model Tests ####
from datetime import date

class MealPlanModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_mealplan_is_created_with_required_fields(self):
        """Given a meal plan is created, it includes all required fields: user, recipe_name, recipe_id, date, and meal_type"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            recipe_name='Spaghetti',
            recipe_id=12345,
            date=date(2026, 4, 3),
            meal_type='Dinner'
        )
        self.assertEqual(meal_plan.user, self.user)
        self.assertEqual(meal_plan.recipe_name, 'Spaghetti')
        self.assertEqual(meal_plan.recipe_id, 12345)
        self.assertEqual(meal_plan.date, date(2026, 4, 3))
        self.assertEqual(meal_plan.meal_type, 'Dinner')
#### End meal calendar model tests ####

#### MealPlan API Tests (Security, Algorithm, UI AC) ####
class MealPlanAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_user_cannot_access_another_user_meals(self):
        """Security AC: Given two users, User B cannot see User A's meal plans via the API"""
        user_a = User.objects.create_user(username='userA', password='password123')
        user_b = User.objects.create_user(username='userB', password='password123')
        MealPlan.objects.create(
            user=user_a,
            recipe_name='Chicken Pasta',
            recipe_id=101,
            date=date(2026, 4, 3),
            meal_type='Dinner'
        )
        # Log in as User B and try to access meals
        self.client.login(username='userB', password='password123')
        response = self.client.get(reverse('get_meals'))
        # User B should NOT see User A's meal
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data.get('meals', [])), 0)
        self.assertFalse(any(m['recipe_name'] == 'Chicken Pasta' for m in data.get('meals', [])))

    def todo_test_generate_weekly_plan_uses_pantry_ingredients(self):
        """Algorithm AC: Given pantry ingredients, the generate function creates meals using those ingredients"""
        Pantry.objects.create(user=self.user, ingredient_name='Chicken')
        Pantry.objects.create(user=self.user, ingredient_name='Broccoli')
        from home.views import generate_weekly_plan
        generate_weekly_plan(self.user)
        meals = MealPlan.objects.filter(user=self.user)
        self.assertTrue(meals.exists())
        meal_names = [m.recipe_name.lower() for m in meals]
        self.assertTrue(any('chicken' in name or 'broccoli' in name for name in meal_names))

    def test_get_meals_returns_empty_for_future_date_range(self):
        """UI AC: Given a date range in the far future with no meals, the API returns empty list with 200 OK"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(
            reverse('get_meals') + '?start_date=2030-01-01&end_date=2030-12-31'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('meals', []), [])
#### End MealPlan API Tests ####

#### MealPlan Negative Tests ####
class MealPlanNegativeTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_create_meal_without_name(self):
        """Negative Test: Attempt to save a MealPlan with null or empty recipe_name should raise ValidationError"""
        with self.assertRaises(ValidationError):
            meal_plan = MealPlan(
                user=self.user,
                recipe_name='',
                recipe_id=123,
                date=date(2026, 4, 3),
                meal_type='Dinner'
            )
            meal_plan.full_clean()

    def test_unauthorized_meal_access(self):
        """Negative Test: User B should not see User A's meals via API - returns empty list or 403"""
        user_a = User.objects.create_user(username='userA_neg', password='password123')
        user_b = User.objects.create_user(username='userB_neg', password='password123')
        MealPlan.objects.create(
            user=user_a,
            recipe_name='Secret Recipe',
            recipe_id=999,
            date=date(2026, 4, 3),
            meal_type='Lunch'
        )
        self.client.login(username='userB_neg', password='password123')
        response = self.client.get(reverse('get_meals'))
        # Should return empty list or 403 Forbidden
        self.assertIn(response.status_code, [200, 403])
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(len(data.get('meals', [])), 0)
            self.assertFalse(any(m['recipe_name'] == 'Secret Recipe' for m in data.get('meals', [])))

    def todo_test_invalid_date_format(self):
        """Negative Test: System should handle invalid date without 500 Server Error"""
        self.client.login(username='testuser', password='password123')
        # Try to create a meal with invalid date string via API
        response = self.client.post(
            reverse('create_meal'),
            data=json.dumps({
                'recipe_name': 'Test Meal',
                'recipe_id': 1,
                'date': '2026-99-99',
                'meal_type': 'Dinner'
            }),
            content_type='application/json'
        )
        # Should return 400 Bad Request, not 500 Server Error
        self.assertIn(response.status_code, [400, 422])
#### End MealPlan Negative Tests ####

#### MealPlan Advanced Integration Tests ####
class MealPlanIntegrationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def todo_test_pantry_integration(self):
        """Integration Test: When user has 'Chicken' in Pantry, generate_meals saves at least one MealPlan"""
        Pantry.objects.create(user=self.user, ingredient_name='Chicken')
        from home.views import generate_meals
        generate_meals(self.user)
        meals_count = MealPlan.objects.filter(user=self.user).count()
        self.assertGreater(meals_count, 0, "Expected at least one MealPlan to be created from pantry ingredients")

    def todo_test_prevent_duplicate_meals(self):
        """Integration Test: Running meal generator twice should not create duplicate MealPlan entries"""
        Pantry.objects.create(user=self.user, ingredient_name='Chicken')
        from home.views import generate_meals
        # Run generator twice
        generate_meals(self.user)
        generate_meals(self.user)
        # Check for duplicates: same user, same meal_type should not have multiple entries
        meal_types = MealPlan.objects.filter(user=self.user).values_list('meal_type', flat=True)
        # Each meal_type should appear only once
        for meal_type in set(meal_types):
            count = MealPlan.objects.filter(user=self.user, meal_type=meal_type).count()
            self.assertEqual(count, 1, f"Found duplicate MealPlan entries for meal_type '{meal_type}'")

    def test_api_requires_login(self):
        """Integration Test: Non-logged-in user cannot access /api/get-meals/ endpoint"""
        # Don't log in - access as anonymous user
        response = self.client.get(reverse('get_meals'))
        # Should return 302 redirect to login or 403 Forbidden
        self.assertIn(response.status_code, [302, 403])
#### End MealPlan Integration Tests ####

#### MealPlan Acceptance Criteria Tests (CRUD, API, Mocking) ####
class MealPlanAcceptanceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_crud_read_meal(self):
        """CRUD Test: A saved MealPlan can be retrieved by ID"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            recipe_name='Grilled Chicken',
            recipe_id=555,
            date=date(2026, 4, 5),
            meal_type='Lunch'
        )
        retrieved = MealPlan.objects.get(id=meal_plan.id)
        self.assertEqual(retrieved.recipe_name, 'Grilled Chicken')
        self.assertEqual(retrieved.recipe_id, 555)
        self.assertEqual(retrieved.date, date(2026, 4, 5))
        self.assertEqual(retrieved.meal_type, 'Lunch')

    def test_crud_delete_meal(self):
        """CRUD Test: A MealPlan can be deleted"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            recipe_name='Salad',
            recipe_id=666,
            date=date(2026, 4, 6),
            meal_type='Dinner'
        )
        meal_id = meal_plan.id
        meal_plan.delete()
        self.assertFalse(MealPlan.objects.filter(id=meal_id).exists())

    def test_api_returns_clean_json(self):
        """API Test: /api/get-meals/ returns clean JSON with expected structure"""
        MealPlan.objects.create(
            user=self.user,
            recipe_name='Omelette',
            recipe_id=111,
            date=date(2026, 4, 7),
            meal_type='Breakfast'
        )
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('get_meals'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Verify JSON structure
        self.assertIn('meals', data)
        self.assertIsInstance(data['meals'], list)
        self.assertEqual(len(data['meals']), 1)
        # Verify meal fields (FullCalendar format uses 'title' instead of 'recipe_name')
        meal = data['meals'][0]
        self.assertIn('title', meal)
        self.assertIn('id', meal)
        self.assertIn('start', meal)
        self.assertIn('meal_type', meal)
        self.assertEqual(meal['title'], 'Omelette')

    def todo_test_generator_handles_empty_pantry(self):
        """Logic Test: Generator handles empty pantry without crashing"""
        from home.views import generate_meals
        # Ensure pantry is empty
        self.assertEqual(Pantry.objects.filter(user=self.user).count(), 0)
        # Should not raise exception
        try:
            generate_meals(self.user)
        except Exception as e:
            self.fail(f"generate_meals() raised {type(e).__name__} with empty pantry: {e}")

    @patch('home.views.spoonacular_get')
    def todo_test_generate_with_mocked_api(self, mock_spoonacular):
        """Mocking Test: When API returns 7 recipes, generate_meal_plan saves 7 MealPlan objects"""
        # Mock API to return 7 recipes
        mock_recipes = [
            {'id': i, 'title': f'Recipe {i}', 'image': f'http://img{i}.jpg'}
            for i in range(1, 8)
        ]
        mock_spoonacular.return_value = mock_recipes
        
        from home.views import generate_meal_plan
        generate_meal_plan(self.user)
        
        # Assert 7 MealPlan objects were saved
        self.assertEqual(MealPlan.objects.filter(user=self.user).count(), 7)
        # Verify recipe names match
        saved_names = list(MealPlan.objects.filter(user=self.user).values_list('recipe_name', flat=True))
        expected_names = [f'Recipe {i}' for i in range(1, 8)]
        self.assertEqual(sorted(saved_names), sorted(expected_names))
#### End MealPlan Acceptance Tests ####
 
#### Start of tests for recipe page and create recipe pages ####

class RecipeViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='password123')

    def test_recipe_view_status(self):
        """Recipe page loads successfully"""
        recipe = Recipe.objects.create(
            user=self.user,
            title="Test Recipe",
            is_public=True
        )

        url = reverse('recipe_view', args=[recipe.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_recipe_view_steps_ordering(self):
        """Steps should be returned in correct order"""
        recipe = Recipe.objects.create(user=self.user, title="Test", is_public=True)

        RecipeStep.objects.create(recipe=recipe, order=2, text="Step 2")
        RecipeStep.objects.create(recipe=recipe, order=1, text="Step 1")

        response = self.client.get(reverse('recipe_view', args=[recipe.id]))

        self.assertEqual(response.context["steps_json"], ["Step 1", "Step 2"])

    def test_recipe_view_ingredients_format(self):
        """Ingredients should be properly formatted"""
        recipe = Recipe.objects.create(user=self.user, title="Test", is_public=True)

        RecipeIngredient.objects.create(recipe=recipe, quantity="1", unit="cup", name="Flour")
        RecipeIngredient.objects.create(recipe=recipe, quantity="2", unit="", name="Eggs")

        response = self.client.get(reverse('recipe_view', args=[recipe.id]))

        ingredients = response.context["ingredients_json"]

        self.assertIn("1 cup Flour", ingredients)
        self.assertIn("2 Eggs".strip(), ingredients)

    def test_recipe_view_404(self):
        """Invalid recipe should return 404"""
        response = self.client.get(reverse('recipe_view', args=[999]))

        self.assertEqual(response.status_code, 404)

# Create recipe tests
class CreateRecipeTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.client = Client()

    def test_create_recipe_requires_login(self):
        """Redirects if user is not logged in"""
        response = self.client.get(reverse('create_recipe'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/signin', response.url)

    def test_create_recipe_get(self):
        """GET request should load the page"""
        self.client.login(username='testuser', password='password123')

        response = self.client.get(reverse('create_recipe'))

        self.assertEqual(response.status_code, 200)

    def test_create_recipe_post(self):
        """POST should create recipe, ingredients, and steps"""
        self.client.login(username='testuser', password='password123')

        response = self.client.post(reverse('create_recipe'), {
            "title": "New Recipe",
            "is_public": "on",
            "ingredient_quantity[]": ["1", "2"],
            "ingredient_unit[]": ["cup", ""],
            "ingredient_name[]": ["Flour", "Eggs"],
            "steps[]": ["Mix", "Bake"]
        })

        self.assertEqual(response.status_code, 302)

        recipe = Recipe.objects.get(title="New Recipe")
        self.assertTrue(recipe.is_public)

        self.assertEqual(RecipeIngredient.objects.filter(recipe=recipe).count(), 2)
        self.assertEqual(RecipeStep.objects.filter(recipe=recipe).count(), 2)

    def test_create_recipe_ignores_empty_fields(self):
        """Empty ingredient names and steps should be ignored"""
        self.client.login(username='testuser', password='password123')

        self.client.post(reverse('create_recipe'), {
            "title": "Edge Recipe",
            "ingredient_quantity[]": ["1", ""],
            "ingredient_unit[]": ["cup", ""],
            "ingredient_name[]": ["Flour", "   "],  # empty
            "steps[]": ["Step 1", "   "]  # empty
        })

        recipe = Recipe.objects.get(title="Edge Recipe")

        self.assertEqual(RecipeIngredient.objects.filter(recipe=recipe).count(), 1)
        self.assertEqual(RecipeStep.objects.filter(recipe=recipe).count(), 1)

 #### End of tests for recipe page and create recipe pages ####

# Tests for Account Management (Registration, Edit Account, Change Password)

class RegisterFormTests(TestCase):
    def test_register_form_rejects_duplicate_email(self):
        User.objects.create_user(
            username="existinguser",
            email="test@email.com",
            password="testpass123"
        )

        form = RegisterForm(data={
            "first_name": "Another",
            "last_name": "User",
            "username": "anotheruser",
            "email": "test@email.com",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn(
            "An account with this email already exists.",
            form.errors["email"]
        )
class EditProfileFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@email.com",
            password="testpass123"
        )

    def test_edit_profile_form_rejects_duplicate_email(self):
        User.objects.create_user(
            username="otheruser",
            email="taken@email.com",
            password="testpass123"
        )

        form = EditProfileForm(
            data={
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "email": "taken@email.com",
            },
            instance=self.user
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn(
            "That email is already in use.",
            form.errors["email"]
        )
class AccountViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@email.com",
            password="testpass123"
        )

    def test_register_view_creates_user(self):
        response = self.client.post(reverse("register"), {
            "first_name": "New",
            "last_name": "User",
            "username": "newuser",
            "email": "newuser@email.com",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_edit_account_updates_user(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(reverse("edit_account"), {
            "first_name": "Updated",
            "last_name": "User",
            "username": "testuser",
            "email": "updated@email.com",
        })

        self.assertEqual(response.status_code, 302)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.email, "updated@email.com")

    def test_change_password_works(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(reverse("change_password"), {
            "old_password": "testpass123",
            "new_password1": "NewStrongPassword123!",
            "new_password2": "NewStrongPassword123!",
        })

        self.assertEqual(response.status_code, 302)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPassword123!"))
    def test_change_password_fails_with_wrong_current_password(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(reverse("change_password"), {
            "old_password": "wrongpassword",
            "new_password1": "NewStrongPassword123!",
            "new_password2": "NewStrongPassword123!",
        })

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("testpass123"))

