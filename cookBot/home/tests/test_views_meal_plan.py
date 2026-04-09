import json
import urllib.error
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from home.models import MealPlan, Pantry


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
        self.client.login(username='userB', password='password123')
        response = self.client.get(reverse('get_meals'))
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
        self.assertIn(response.status_code, [200, 403])
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(len(data.get('meals', [])), 0)
            self.assertFalse(any(m['recipe_name'] == 'Secret Recipe' for m in data.get('meals', [])))

    def todo_test_invalid_date_format(self):
        """Negative Test: System should handle invalid date without 500 Server Error"""
        self.client.login(username='testuser', password='password123')
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
        self.assertIn(response.status_code, [400, 422])


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
        generate_meals(self.user)
        generate_meals(self.user)
        meal_types = MealPlan.objects.filter(user=self.user).values_list('meal_type', flat=True)
        for meal_type in set(meal_types):
            count = MealPlan.objects.filter(user=self.user, meal_type=meal_type).count()
            self.assertEqual(count, 1, f"Found duplicate MealPlan entries for meal_type '{meal_type}'")

    def test_api_requires_login(self):
        """Integration Test: Non-logged-in user cannot access /api/get-meals/ endpoint"""
        response = self.client.get(reverse('get_meals'))
        self.assertIn(response.status_code, [302, 403])


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
        self.assertIn('meals', data)
        self.assertIsInstance(data['meals'], list)
        self.assertEqual(len(data['meals']), 1)
        meal = data['meals'][0]
        self.assertIn('title', meal)
        self.assertIn('id', meal)
        self.assertIn('start', meal)
        self.assertIn('meal_type', meal)
        self.assertEqual(meal['title'], 'Omelette')

    def todo_test_generator_handles_empty_pantry(self):
        """Logic Test: Generator handles empty pantry without crashing"""
        from home.views import generate_meals
        self.assertEqual(Pantry.objects.filter(user=self.user).count(), 0)
        try:
            generate_meals(self.user)
        except Exception as e:
            self.fail(f"generate_meals() raised {type(e).__name__} with empty pantry: {e}")

    @patch('home.views.spoonacular_get')
    def todo_test_generate_with_mocked_api(self, mock_spoonacular):
        """Mocking Test: When API returns 7 recipes, generate_meal_plan saves 7 MealPlan objects"""
        mock_recipes = [
            {'id': i, 'title': f'Recipe {i}', 'image': f'http://img{i}.jpg'}
            for i in range(1, 8)
        ]
        mock_spoonacular.return_value = mock_recipes
        from home.views import generate_meal_plan
        generate_meal_plan(self.user)
        self.assertEqual(MealPlan.objects.filter(user=self.user).count(), 7)
        saved_names = list(MealPlan.objects.filter(user=self.user).values_list('recipe_name', flat=True))
        expected_names = [f'Recipe {i}' for i in range(1, 8)]
        self.assertEqual(sorted(saved_names), sorted(expected_names))


class MealPlanViewTests(TestCase):
    """
    Tests for get_meals and generate_meal_plan views, extracted from MissingCoverageTests.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_get_meals_json_success(self):
        """Test views.py lines 328-354: get_meals_json returns meal plans"""
        self.client.login(username='testuser', password='password123')
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
        test_date = date(2026, 6, 15)
        MealPlan.objects.create(
            user=self.user,
            recipe_name='Summer Meal',
            recipe_id=456,
            date=test_date,
            meal_type='Lunch'
        )
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
        Pantry.objects.create(user=self.user, ingredient_name='Chicken')
        Pantry.objects.create(user=self.user, ingredient_name='Rice')
        mock_recipes = [{'id': i, 'title': f'Recipe {i}'} for i in range(1, 8)]
        mock_spoonacular.return_value = mock_recipes
        response = self.client.post(reverse('generate_meal_plan'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['meals_count'], 7)
        meals_count = MealPlan.objects.filter(user=self.user).count()
        self.assertEqual(meals_count, 7)

    @patch('home.views.spoonacular_get')
    def test_generate_meal_plan_api_failure(self, mock_spoonacular):
        """Test views.py: generate_meal_plan falls back to suggested recipes on API failure"""
        self.client.login(username='testuser', password='password123')
        Pantry.objects.create(user=self.user, ingredient_name='Chicken')
        mock_spoonacular.side_effect = urllib.error.HTTPError(
            url="test", code=500, msg="Internal Server Error", hdrs={}, fp=None
        )
        response = self.client.post(reverse('generate_meal_plan'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('meals_count', data)
        self.assertEqual(data['meals_count'], 7)
        meals_count = MealPlan.objects.filter(user=self.user).count()
        self.assertEqual(meals_count, 7)

    @patch('home.views.spoonacular_get')
    def test_generate_meal_plan_empty_api_response(self, mock_spoonacular):
        """Test generate_meal_plan handles empty API response with fallback"""
        self.client.login(username='testuser', password='password123')
        Pantry.objects.create(user=self.user, ingredient_name='Rice')
        mock_spoonacular.return_value = []
        response = self.client.post(reverse('generate_meal_plan'))
        self.assertIn(response.status_code, [200, 502])

    def test_calendar_view_requires_login(self):
        """Test that calendar_view redirects when not logged in"""
        response = self.client.get(reverse('calendar'))
        self.assertIn(response.status_code, [302, 403])

    def test_calendar_view(self):
        """Test calendar page loads for logged-in user"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('calendar'))
        self.assertEqual(response.status_code, 200)