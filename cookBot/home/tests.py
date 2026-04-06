import json
from io import BytesIO
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from home.models import Pantry, Recipe, RecipeIngredient, RecipeRating, RecipeStep, ChatSession, ChatMessage, Recipe, RecipeIngredient
from django.core.cache import cache
from home.chefBot import collect_context_from_recipes, build_messages, SYSTEM_PROMPT

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

### Start of ChefBot testing ###

class TestContextFromRecipes(TestCase):
    
    def test_spoonacular_recipes_appear_in_context(self):
        """Spoonacular recipe titles and ingredients show up in the context block."""
        spoonacular = [
            {
                'title': 'Chicken Fried Rice',
                'used_ingredients': ['chicken', 'rice'],
                'missed_ingredients': [],
            }
        ]
        context = collect_context_from_recipes(spoonacular_recipes=spoonacular)
        self.assertIn('Chicken Fried Rice', context)
        self.assertIn('chicken', context)
        self.assertIn('rice', context)
 
    def test_saved_recipes_appear_in_context(self):
        """Saved recipe titles and ingredients show up in the context block."""
        saved = [
            {
                'title': 'Pasta Carbonara',
                'ingredients': [
                    {'quantity': '200', 'unit': 'g', 'name': 'spaghetti'},
                    {'quantity': '2', 'unit': '', 'name': 'eggs'},
                ],
            }
        ]
        context = collect_context_from_recipes(saved_recipes=saved)
        self.assertIn('Pasta Carbonara', context)
        self.assertIn('spaghetti', context)
        self.assertIn('eggs', context)
 
    def test_both_spoonacular_and_saved_recipes_appear_in_context(self):
        """Both Spoonacular and saved recipes appear together in the context block."""
        spoonacular = [
            {
                'title': 'Chicken Soup',
                'used_ingredients': ['chicken'],
                'missed_ingredients': ['broth'],
            }
        ]
        saved = [
            {
                'title': 'Beef Tacos',
                'ingredients': [{'quantity': '300', 'unit': 'g', 'name': 'beef'}],
            }
        ]
        context = collect_context_from_recipes(
            spoonacular_recipes=spoonacular,
            saved_recipes=saved
        )
        self.assertIn('Chicken Soup', context)
        self.assertIn('Beef Tacos', context)
 
    def test_empty_inputs_return_empty_string(self):
        """No recipes passed in returns an empty string."""
        context = collect_context_from_recipes()
        self.assertEqual(context, '')

class TestBuildMessages(TestCase):
    def test_system_prompt_is_first_message(self):
        """The first message is always the system prompt."""
        messages = build_messages([])
        self.assertEqual(messages[0]['role'], 'system')
        self.assertIn('ChefBot', messages[0]['content'])
 
    def test_conversation_history_appended_after_system(self):
        """Conversation history is appended after the system prompt."""
        history = [
            {'role': 'user', 'content': 'What can I cook?'},
            {'role': 'assistant', 'content': 'Here is a recipe!'},
        ]
        messages = build_messages(history)
        self.assertEqual(messages[1]['role'], 'user')
        self.assertEqual(messages[2]['role'], 'assistant')
 
    def test_recipe_context_injected_into_system_prompt(self):
        """When recipes are passed, context is injected into the system prompt."""
        spoonacular = [
            {
                'title': 'Chicken Fried Rice',
                'used_ingredients': ['chicken'],
                'missed_ingredients': [],
            }
        ]
        messages = build_messages([], spoonacular_recipes=spoonacular)
        system_content = messages[0]['content']
        self.assertIn('USER RECIPE CONTEXT', system_content)
        self.assertIn('Chicken Fried Rice', system_content)
 
    def test_no_context_block_when_no_recipes(self):
        """When no recipes are passed, the context block is not added."""
        messages = build_messages([])
        system_content = messages[0]['content']
        self.assertNotIn('USER RECIPE CONTEXT', system_content)
 
    def test_saved_recipes_injected_into_system_prompt(self):
        """Saved recipes are injected into the system prompt."""
        saved = [
            {
                'title': 'Beef Tacos',
                'ingredients': [{'quantity': '300', 'unit': 'g', 'name': 'beef'}],
            }
        ]
        messages = build_messages([], saved_recipes=saved)
        system_content = messages[0]['content']
        self.assertIn('Beef Tacos', system_content)

class TestChatSessionModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.session = ChatSession.objects.create(
            user=self.user,
            spoonacular_context=[],
        )
 
    def test_get_history_returns_messages_in_order(self):
        """get_history() returns messages ordered by timestamp."""
        ChatMessage.objects.create(session=self.session, role='user', content='Hello')
        ChatMessage.objects.create(session=self.session, role='assistant', content='Hi there!')
        history = self.session.get_history()
        self.assertEqual(history[0]['role'], 'user')
        self.assertEqual(history[1]['role'], 'assistant')
 
    def test_get_history_returns_correct_format_for_openai(self):
        """get_history() returns dicts with role and content keys only."""
        ChatMessage.objects.create(session=self.session, role='user', content='Test message')
        history = self.session.get_history()
        self.assertIn('role', history[0])
        self.assertIn('content', history[0])
        self.assertNotIn('id', history[0])
        self.assertNotIn('timestamp', history[0])
 
    def test_get_history_empty_when_no_messages(self):
        """get_history() returns an empty list when no messages exist."""
        history = self.session.get_history()
        self.assertEqual(history, [])
 
    def test_spoonacular_context_stored_on_session(self):
        """Spoonacular recipe context is correctly stored on the session."""
        spoonacular = [{'title': 'Chicken Soup', 'used_ingredients': ['chicken'], 'missed_ingredients': []}]
        session = ChatSession.objects.create(
            user=self.user,
            spoonacular_context=spoonacular,
        )
        self.assertEqual(session.spoonacular_context[0]['title'], 'Chicken Soup')

class TestAiChefBotView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
 
    def test_unauthenticated_user_redirected(self):
        """Unauthenticated users are redirected away from the aiChefBot page."""
        unauthenticated_client = Client()
        response = unauthenticated_client.get('/aiChefBot/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/signin', response.url)
 
    @patch('home.spoonacular.spoonacular_get', return_value=[])
    def test_aichefbot_page_loads(self, mock_spoon):
        """aiChefBot page loads successfully for a logged in user."""
        response = self.client.get('/aiChefBot/')
        self.assertEqual(response.status_code, 200)
 
    @patch('home.spoonacular.spoonacular_get')
    def test_spoonacular_recipes_passed_to_template(self, mock_spoon):
        """Spoonacular recipes are fetched and passed to the template context."""
        mock_spoon.return_value = [
            {
                'title': 'Chicken Fried Rice',
                'usedIngredients': [{'name': 'chicken'}],
                'missedIngredients': [],
            }
        ]
        self.user.pantry_items.create(ingredient_name='chicken')
        response = self.client.get('/aiChefBot/')
        self.assertEqual(response.status_code, 200)
        spoon_recipes = response.context['spoonacular_recipes']
        titles = [r['title'] for r in spoon_recipes]
        self.assertIn('Chicken Fried Rice', titles)
 
    @patch('home.spoonacular.spoonacular_get', return_value=[])
    def test_saved_recipes_passed_to_template(self, mock_spoon):
        """User's saved recipes are passed to the template context."""
        Recipe.objects.create(user=self.user, title='Pasta Carbonara', is_public=False)
        response = self.client.get('/aiChefBot/')
        self.assertEqual(response.status_code, 200)
        saved_recipes = response.context['saved_recipes']
        titles = [r['title'] for r in saved_recipes]
        self.assertIn('Pasta Carbonara', titles)
 
    @patch('home.spoonacular.spoonacular_get', return_value=[])
    def test_chat_session_created_on_page_load(self, mock_spoon):
        """A new ChatSession is created each time the aiChefBot page loads."""
        self.client.get('/aiChefBot/')
        self.assertTrue(ChatSession.objects.filter(user=self.user).exists())

class TestAiChefBotChat(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        self.session = ChatSession.objects.create(
            user=self.user,
            spoonacular_context=[],
        )
 
    def post_chat(self, message, session_id=None):
        return self.client.post(
            '/aiChefBot/chat/',
            data=json.dumps({
                'session_id': session_id or self.session.id,
                'message': message,
            }),
            content_type='application/json',
        )
 
    @patch('home.views.call_openai', return_value='Here is a great recipe!')
    def test_successful_chat_returns_reply(self, mock_openai):
        """A valid message returns a reply from ChefBot."""
        response = self.post_chat('What can I cook with chicken?')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('reply', data)
        self.assertEqual(data['reply'], 'Here is a great recipe!')
 
    @patch('home.views.call_openai', return_value='Here is a great recipe!')
    def test_user_message_saved_to_db(self, mock_openai):
        """User message is saved to the database after sending."""
        self.post_chat('What can I cook with chicken?')
        self.assertTrue(
            ChatMessage.objects.filter(
                session=self.session,
                role='user',
                content='What can I cook with chicken?'
            ).exists()
        )
 
    @patch('home.views.call_openai', return_value='Here is a great recipe!')
    def test_assistant_reply_saved_to_db(self, mock_openai):
        """ChefBot reply is saved to the database after responding."""
        self.post_chat('What can I cook with chicken?')
        self.assertTrue(
            ChatMessage.objects.filter(
                session=self.session,
                role='assistant',
                content='Here is a great recipe!'
            ).exists()
        )
 
    @patch('home.views.call_openai', return_value='Reply 3')
    def test_full_conversation_history_sent_to_openai(self, mock_openai):
        """The full conversation history is passed to call_openai on each message."""
        ChatMessage.objects.create(session=self.session, role='user', content='First message')
        ChatMessage.objects.create(session=self.session, role='assistant', content='First reply')
        self.post_chat('Second message')
        call_args = mock_openai.call_args
        history = call_args[1]['conversation_history'] if call_args[1] else call_args[0][0]
        self.assertEqual(len(history), 3)  # 2 existing + new user message
 
    @patch('home.views.call_openai', return_value='Recipe reply')
    def test_spoonacular_context_passed_to_openai(self, mock_openai):
        """Spoonacular context stored on the session is passed to call_openai."""
        self.session.spoonacular_context = [
            {'title': 'Chicken Soup', 'used_ingredients': ['chicken'], 'missed_ingredients': []}
        ]
        self.session.save()
        self.post_chat('What can I cook?')
        call_args = mock_openai.call_args
        spoon_arg = call_args[1].get('spoonacular_recipes') or call_args[0][1]
        self.assertEqual(spoon_arg[0]['title'], 'Chicken Soup')
 
    @patch('home.views.call_openai', return_value='Recipe reply')
    def test_saved_recipes_passed_to_openai(self, mock_openai):
        """User's saved recipes are passed to call_openai."""
        Recipe.objects.create(user=self.user, title='Beef Tacos', is_public=False)
        self.post_chat('What can I cook?')
        call_args = mock_openai.call_args
        saved_arg = call_args[1].get('saved_recipes') or call_args[0][2]
        titles = [r['title'] for r in saved_arg]
        self.assertIn('Beef Tacos', titles)
 
    def test_empty_message_returns_400(self):
        """An empty message returns a 400 error."""
        response = self.post_chat('')
        self.assertEqual(response.status_code, 400)
 
    def test_invalid_session_id_returns_404(self):
        """An invalid session ID returns a 404 error."""
        response = self.post_chat('Hello', session_id=999999)
        self.assertEqual(response.status_code, 404)
 
    def test_user_cannot_access_another_users_session(self):
        """A user cannot send messages to another user's chat session."""
        other_user = User.objects.create_user(username='otheruser', password='testpass123')
        other_session = ChatSession.objects.create(user=other_user, spoonacular_context=[])
        response = self.post_chat('Hello', session_id=other_session.id)
        self.assertEqual(response.status_code, 404)
 
    @patch('home.views.call_openai', side_effect=Exception('OpenAI is down'))
    def test_openai_failure_returns_500(self, mock_openai):
        """An OpenAI API failure returns a 500 error."""
        response = self.post_chat('What can I cook?')
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertIn('error', data)
 