import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse

from home.models import MealPlan, Pantry
from home.chefBot import build_macro_cuisine_pantry_context, build_meal_plan_prompt

# 21 mock meals — 7 days x 3 meal types
MOCK_AI_MEALS = [
    {
        "day": day,
        "meal_type": meal_type,
        "recipe_name": f"Mock {meal_type} Day {day}",
        "calories": 500,
        "protein": 30,
        "fat": 15,
        "carbs": 50,
    }
    for day in range(1, 8)
    for meal_type in ["Breakfast", "Lunch", "Dinner"]
]


class MealPlanAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )

    def test_user_cannot_access_another_user_meals(self):
        """Security AC: Given two users, User B cannot see User A's meal plans via the API"""
        user_a = User.objects.create_user(username="userA", password="password123")
        User.objects.create_user(username="userB", password="password123")
        MealPlan.objects.create(
            user=user_a,
            recipe_name="Chicken Pasta",
            recipe_id=101,
            date=date(2026, 4, 3),
            meal_type="Dinner",
        )
        self.client.login(username="userB", password="password123")
        response = self.client.get(reverse("get_meals"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data.get("meals", [])), 0)
        self.assertFalse(
            any(m["recipe_name"] == "Chicken Pasta" for m in data.get("meals", []))
        )

    def todo_test_generate_weekly_plan_uses_pantry_ingredients(self):
        """Algorithm AC: Given pantry ingredients, the generate function creates meals using those ingredients"""
        Pantry.objects.create(user=self.user, ingredient_name="Chicken")
        Pantry.objects.create(user=self.user, ingredient_name="Broccoli")
        from home.views import generate_weekly_plan

        generate_weekly_plan(self.user)
        meals = MealPlan.objects.filter(user=self.user)
        self.assertTrue(meals.exists())
        meal_names = [m.recipe_name.lower() for m in meals]
        self.assertTrue(
            any("chicken" in name or "broccoli" in name for name in meal_names)
        )

    def test_get_meals_returns_empty_for_future_date_range(self):
        """UI AC: Given a date range in the far future with no meals, the API returns empty list with 200 OK"""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(
            reverse("get_meals") + "?start_date=2030-01-01&end_date=2030-12-31"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("meals", []), [])


class MealPlanNegativeTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )

    def test_create_meal_without_name(self):
        """Negative Test: Attempt to save a MealPlan with null or empty recipe_name should raise ValidationError"""
        with self.assertRaises(ValidationError):
            meal_plan = MealPlan(
                user=self.user,
                recipe_name="",
                recipe_id=123,
                date=date(2026, 4, 3),
                meal_type="Dinner",
            )
            meal_plan.full_clean()

    def test_unauthorized_meal_access(self):
        """Negative Test: User B should not see User A's meals via API - returns empty list or 403"""
        user_a = User.objects.create_user(username="userA_neg", password="password123")
        User.objects.create_user(username="userB_neg", password="password123")
        MealPlan.objects.create(
            user=user_a,
            recipe_name="Secret Recipe",
            recipe_id=999,
            date=date(2026, 4, 3),
            meal_type="Lunch",
        )
        self.client.login(username="userB_neg", password="password123")
        response = self.client.get(reverse("get_meals"))
        self.assertIn(response.status_code, [200, 403])
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(len(data.get("meals", [])), 0)
            self.assertFalse(
                any(m["recipe_name"] == "Secret Recipe" for m in data.get("meals", []))
            )

    def todo_test_invalid_date_format(self):
        """Negative Test: System should handle invalid date without 500 Server Error"""
        self.client.login(username="testuser", password="password123")
        response = self.client.post(
            reverse("create_meal"),
            data=json.dumps(
                {
                    "recipe_name": "Test Meal",
                    "recipe_id": 1,
                    "date": "2026-99-99",
                    "meal_type": "Dinner",
                }
            ),
            content_type="application/json",
        )
        self.assertIn(response.status_code, [400, 422])


class MealPlanIntegrationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )

    def todo_test_pantry_integration(self):
        """Integration Test: When user has 'Chicken' in Pantry, generate_meals saves at least one MealPlan"""
        Pantry.objects.create(user=self.user, ingredient_name="Chicken")
        from home.views import generate_meals

        generate_meals(self.user)
        meals_count = MealPlan.objects.filter(user=self.user).count()
        self.assertGreater(
            meals_count,
            0,
            "Expected at least one MealPlan to be created from pantry ingredients",
        )

    def todo_test_prevent_duplicate_meals(self):
        """Integration Test: Running meal generator twice should not create duplicate MealPlan entries"""
        Pantry.objects.create(user=self.user, ingredient_name="Chicken")
        from home.views import generate_meals

        generate_meals(self.user)
        generate_meals(self.user)
        meal_types = MealPlan.objects.filter(user=self.user).values_list(
            "meal_type", flat=True
        )
        for meal_type in set(meal_types):
            count = MealPlan.objects.filter(user=self.user, meal_type=meal_type).count()
            self.assertEqual(
                count,
                1,
                f"Found duplicate MealPlan entries for meal_type '{meal_type}'",
            )

    def test_api_requires_login(self):
        """Integration Test: Non-logged-in user cannot access /api/get-meals/ endpoint"""
        response = self.client.get(reverse("get_meals"))
        self.assertIn(response.status_code, [302, 403])


class MealPlanAcceptanceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )

    def test_crud_read_meal(self):
        """CRUD Test: A saved MealPlan can be retrieved by ID"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            recipe_name="Grilled Chicken",
            recipe_id=555,
            date=date(2026, 4, 5),
            meal_type="Lunch",
        )
        retrieved = MealPlan.objects.get(id=meal_plan.id)
        self.assertEqual(retrieved.recipe_name, "Grilled Chicken")
        self.assertEqual(retrieved.recipe_id, 555)
        self.assertEqual(retrieved.date, date(2026, 4, 5))
        self.assertEqual(retrieved.meal_type, "Lunch")

    def test_crud_delete_meal(self):
        """CRUD Test: A MealPlan can be deleted"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            recipe_name="Salad",
            recipe_id=666,
            date=date(2026, 4, 6),
            meal_type="Dinner",
        )
        meal_id = meal_plan.id
        meal_plan.delete()
        self.assertFalse(MealPlan.objects.filter(id=meal_id).exists())

    def test_api_returns_clean_json(self):
        """API Test: /api/get-meals/ returns clean JSON with expected structure"""
        MealPlan.objects.create(
            user=self.user,
            recipe_name="Omelette",
            recipe_id=111,
            date=date.today(),
            meal_type="Breakfast",
        )
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("get_meals"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("meals", data)
        self.assertIsInstance(data["meals"], list)
        self.assertEqual(len(data["meals"]), 1)
        meal = data["meals"][0]
        self.assertIn("title", meal)
        self.assertIn("id", meal)
        self.assertIn("start", meal)
        self.assertIn("meal_type", meal)
        self.assertEqual(meal["title"], "Omelette")

    def todo_test_generator_handles_empty_pantry(self):
        """Logic Test: Generator handles empty pantry without crashing"""
        from home.views import generate_meals

        self.assertEqual(Pantry.objects.filter(user=self.user).count(), 0)
        try:
            generate_meals(self.user)
        except Exception as e:
            self.fail(
                f"generate_meals() raised {type(e).__name__} with empty pantry: {e}"
            )

    @patch("home.views.spoonacular_get")
    def todo_test_generate_with_mocked_api(self, mock_spoonacular):
        """Mocking Test: When API returns 7 recipes, generate_meal_plan saves 7 MealPlan objects"""
        mock_recipes = [
            {"id": i, "title": f"Recipe {i}", "image": f"http://img{i}.jpg"}
            for i in range(1, 8)
        ]
        mock_spoonacular.return_value = mock_recipes
        from home.views import generate_meal_plan

        generate_meal_plan(self.user)
        self.assertEqual(MealPlan.objects.filter(user=self.user).count(), 7)
        saved_names = list(
            MealPlan.objects.filter(user=self.user).values_list(
                "recipe_name", flat=True
            )
        )
        expected_names = [f"Recipe {i}" for i in range(1, 8)]
        self.assertEqual(sorted(saved_names), sorted(expected_names))


class MealPlanViewTests(TestCase):
    """
    Tests for get_meals and generate_meal_plan views, extracted from MissingCoverageTests.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )

    def test_get_meals_json_success(self):
        """Test views.py lines 328-354: get_meals_json returns meal plans"""
        self.client.login(username="testuser", password="password123")
        MealPlan.objects.create(
            user=self.user,
            recipe_name="Test Meal",
            recipe_id=123,
            date=date.today(),
            meal_type="Dinner",
        )
        response = self.client.get(reverse("get_meals"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("meals", data)
        self.assertIsInstance(data["meals"], list)
        self.assertEqual(len(data["meals"]), 1)
        meal = data["meals"][0]
        self.assertEqual(meal["title"], "Test Meal")
        self.assertEqual(meal["meal_type"], "Dinner")

    def test_get_meals_json_with_date_range(self):
        """Test views.py lines 331-350: get_meals_json with custom date range"""
        self.client.login(username="testuser", password="password123")
        test_date = date(2026, 6, 15)
        MealPlan.objects.create(
            user=self.user,
            recipe_name="Summer Meal",
            recipe_id=456,
            date=test_date,
            meal_type="Lunch",
        )
        response = self.client.get(
            reverse("get_meals") + "?start_date=2026-06-01&end_date=2026-06-30"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["meals"]), 1)
        self.assertEqual(data["meals"][0]["title"], "Summer Meal")

    def test_get_meals_json_empty_result(self):
        """Test views.py lines 346-351: get_meals_json returns empty list when no meals"""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("get_meals"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("meals", data)
        self.assertEqual(len(data["meals"]), 0)

    @patch("home.views.generate_meal_plan_with_ai", return_value=MOCK_AI_MEALS)
    def test_generate_meal_plan_empty_pantry(self, mock_ai):
        """Test views.py lines 383-386: generate_meal_plan returns 400 when pantry is empty"""
        self.client.login(username="testuser", password="password123")
        Pantry.objects.filter(user=self.user).delete()
        response = self.client.post(
            reverse("generate_meal_plan"),
            data=json.dumps({"use_pantry": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("empty", data["error"].lower())

    @patch("home.views.generate_meal_plan_with_ai", return_value=MOCK_AI_MEALS)
    def test_generate_meal_plan_success(self, mock_ai):
        """Test views.py lines 391-438: generate_meal_plan creates 21 meals"""
        self.client.login(username="testuser", password="password123")
        Pantry.objects.create(user=self.user, ingredient_name="Chicken")
        Pantry.objects.create(user=self.user, ingredient_name="Rice")

        response = self.client.post(
            reverse("generate_meal_plan"),
            data=json.dumps({"use_pantry": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["meals_count"], 21)
        self.assertEqual(MealPlan.objects.filter(user=self.user).count(), 21)

    @patch(
        "home.views.generate_meal_plan_with_ai", side_effect=Exception("OpenAI is down")
    )
    def test_generate_meal_plan_api_failure(self, mock_ai):
        """Test views.py: generate_meal_plan falls back to suggested recipes on API failure"""
        self.client.login(username="testuser", password="password123")
        Pantry.objects.create(user=self.user, ingredient_name="Chicken")
        response = self.client.post(
            reverse("generate_meal_plan"),
            data=json.dumps({"use_pantry": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)

    @patch("home.views.generate_meal_plan_with_ai", return_value=[])
    def test_generate_meal_plan_empty_api_response(self, mock_ai):
        """Test generate_meal_plan handles empty API response with fallback"""
        self.client.login(username="testuser", password="password123")
        Pantry.objects.create(user=self.user, ingredient_name="Rice")
        response = self.client.post(
            reverse("generate_meal_plan"),
            data=json.dumps({"use_pantry": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)

    def test_calendar_view_requires_login(self):
        """Test that calendar_view redirects when not logged in"""
        response = self.client.get(reverse("calendar"))
        self.assertIn(response.status_code, [302, 403])

    def test_calendar_view(self):
        """Test calendar page loads for logged-in user"""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("calendar"))
        self.assertEqual(response.status_code, 200)


class AIMealPlanGenerationTests(TestCase):
    """Tests for the new AI-powered meal plan generation endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )
        self.client.login(username="testuser", password="password123")

    def post_generate(self, payload):
        """Helper to POST to generate_meal_plan with mocked OpenAI."""
        with patch("home.views.generate_meal_plan_with_ai", return_value=MOCK_AI_MEALS):
            return self.client.post(
                reverse("generate_meal_plan"),
                data=json.dumps(payload),
                content_type="application/json",
            )

    def test_generate_with_all_fields_and_pantry_on(self):
        """All macros, cuisine, and pantry on — should generate 21 meals."""
        Pantry.objects.create(user=self.user, ingredient_name="Chicken")
        Pantry.objects.create(user=self.user, ingredient_name="Rice")
        response = self.post_generate(
            {
                "calories": 500,
                "protein": 30,
                "fat": 15,
                "carbs": 50,
                "cuisine": "Italian",
                "use_pantry": True,
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(MealPlan.objects.filter(user=self.user).count(), 21)

    def test_generate_with_all_fields_and_pantry_off(self):
        """All macros, cuisine, pantry off — should generate 21 meals without pantry."""
        response = self.post_generate(
            {
                "calories": 500,
                "protein": 30,
                "fat": 15,
                "carbs": 50,
                "cuisine": "Mexican",
                "use_pantry": False,
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(MealPlan.objects.filter(user=self.user).count(), 21)

    def test_generate_with_all_fields_empty(self):
        """No inputs at all — should still generate 21 balanced meals."""
        response = self.post_generate({"use_pantry": False})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(MealPlan.objects.filter(user=self.user).count(), 21)

    def test_generate_with_only_macros(self):
        """Only macros filled, no cuisine, pantry off — should generate 21 meals."""
        response = self.post_generate(
            {
                "calories": 600,
                "protein": 40,
                "fat": 20,
                "carbs": 60,
                "cuisine": None,
                "use_pantry": False,
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(MealPlan.objects.filter(user=self.user).count(), 21)

    def test_generate_with_only_cuisine(self):
        """Only cuisine filled, no macros, pantry off — should generate 21 meals."""
        response = self.post_generate(
            {
                "calories": None,
                "protein": None,
                "fat": None,
                "carbs": None,
                "cuisine": "Japanese",
                "use_pantry": False,
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(MealPlan.objects.filter(user=self.user).count(), 21)

    def test_generate_with_pantry_on_but_empty_pantry(self):
        """Pantry toggle on but pantry is empty — should return 400 error."""
        Pantry.objects.filter(user=self.user).delete()
        response = self.client.post(
            reverse("generate_meal_plan"),
            data=json.dumps({"use_pantry": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("empty", data["error"].lower())

    def test_generate_replaces_existing_meals(self):
        """Generating twice should replace the first week not duplicate it."""
        self.post_generate({"use_pantry": False})
        first_count = MealPlan.objects.filter(user=self.user).count()
        self.post_generate({"use_pantry": False})
        second_count = MealPlan.objects.filter(user=self.user).count()
        self.assertEqual(
            first_count,
            second_count,
            "Duplicate meals were created on second generation",
        )

    def test_generate_saves_macros_to_db(self):
        """Generated meals should have macro values saved to the database."""
        self.post_generate(
            {
                "calories": 500,
                "protein": 30,
                "fat": 15,
                "carbs": 50,
                "use_pantry": False,
            }
        )
        meal = MealPlan.objects.filter(user=self.user).first()
        self.assertEqual(meal.calories, 500)
        self.assertEqual(meal.protein, 30)
        self.assertEqual(meal.fat, 15)
        self.assertEqual(meal.carbs, 50)

    def test_generate_creates_all_three_meal_types(self):
        """Generated plan should contain Breakfast, Lunch, and Dinner."""
        self.post_generate({"use_pantry": False})
        meal_types = set(
            MealPlan.objects.filter(user=self.user).values_list("meal_type", flat=True)
        )
        self.assertIn("Breakfast", meal_types)
        self.assertIn("Lunch", meal_types)
        self.assertIn("Dinner", meal_types)

    def test_generate_covers_seven_days(self):
        """Generated plan should span exactly 7 different dates."""
        self.post_generate({"use_pantry": False})
        dates = set(
            MealPlan.objects.filter(user=self.user).values_list("date", flat=True)
        )
        self.assertEqual(len(dates), 7)

    def test_openai_failure_returns_500(self):
        """If OpenAI fails, the endpoint should return 500."""
        with patch(
            "home.views.generate_meal_plan_with_ai",
            side_effect=Exception("OpenAI is down"),
        ):
            response = self.client.post(
                reverse("generate_meal_plan"),
                data=json.dumps({"use_pantry": False}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)

    def test_get_meals_includes_macros_in_response(self):
        """get_meals_json should include macro fields in the calendar event response."""
        MealPlan.objects.create(
            user=self.user,
            recipe_name="Grilled Chicken",
            date=date.today(),
            meal_type="Dinner",
            calories=500,
            protein=40,
            fat=15,
            carbs=30,
        )
        response = self.client.get(reverse("get_meals"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        meal = data["meals"][0]
        self.assertIn("calories", meal)
        self.assertIn("protein", meal)
        self.assertIn("fat", meal)
        self.assertIn("carbs", meal)
        self.assertEqual(meal["calories"], 500)
        self.assertEqual(meal["protein"], 40)

    def test_unauthenticated_user_cannot_generate(self):
        """Unauthenticated users should be redirected from generate endpoint."""
        unauthenticated_client = Client()
        response = unauthenticated_client.post(
            reverse("generate_meal_plan"),
            data=json.dumps({"use_pantry": False}),
            content_type="application/json",
        )
        self.assertIn(response.status_code, [302, 403])

    def test_invalid_json_body_returns_400(self):
        """Sending invalid JSON should return 400."""
        response = self.client.post(
            reverse("generate_meal_plan"),
            data="not valid json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class ChefBotMealPlanUnitTests(TestCase):
    """Unit tests for chefBot.py meal plan helper functions."""

    def test_build_context_with_all_inputs(self):
        """All macro, cuisine, and pantry inputs should appear in context sections."""
        macro, cuisine, pantry = build_macro_cuisine_pantry_context(
            calories=500,
            protein=30,
            fat=15,
            carbs=50,
            cuisine="Italian",
            pantry_items=["chicken", "rice"],
        )
        self.assertIn("167", macro)
        self.assertIn("10", macro)
        self.assertIn("Italian", cuisine)
        self.assertIn("chicken", pantry)
        self.assertIn("rice", pantry)

    def test_build_context_with_no_inputs(self):
        """Empty inputs should return default fallback strings."""
        macro, cuisine, pantry = build_macro_cuisine_pantry_context()
        self.assertIn("No specific macro targets", macro)
        self.assertIn("No cuisine preference", cuisine)
        self.assertIn("No pantry items provided", pantry)

    def test_build_context_with_only_macros(self):
        """Only macros filled — cuisine and pantry should be defaults."""
        macro, cuisine, pantry = build_macro_cuisine_pantry_context(
            calories=600, protein=40, fat=20, carbs=60
        )
        self.assertIn("200", macro)
        self.assertIn("No cuisine preference", cuisine)
        self.assertIn("No pantry items provided", pantry)

    def test_build_context_with_only_cuisine(self):
        """Only cuisine filled — macros and pantry should be defaults."""
        macro, cuisine, pantry = build_macro_cuisine_pantry_context(cuisine="Japanese")
        self.assertIn("No specific macro targets", macro)
        self.assertIn("Japanese", cuisine)
        self.assertIn("No pantry items provided", pantry)

    def test_build_meal_plan_prompt_contains_context(self):
        """Built prompt should contain all three context sections."""
        macro = "Target macros per meal:\n- Calories per meal: ~500 kcal"
        cuisine = "Cuisine preference: Mexican."
        pantry = "The user has these ingredients: chicken, rice."
        prompt = build_meal_plan_prompt(macro, cuisine, pantry)
        self.assertIn("500", prompt)
        self.assertIn("Mexican", prompt)
        self.assertIn("chicken", prompt)
        self.assertIn("21 meals", prompt)
        self.assertIn("Breakfast", prompt)
        self.assertIn("Lunch", prompt)
        self.assertIn("Dinner", prompt)

    def test_build_meal_plan_prompt_contains_json_format(self):
        """Prompt should instruct OpenAI to return JSON."""
        prompt = build_meal_plan_prompt("macros", "cuisine", "pantry")
        self.assertIn("JSON", prompt)
        self.assertIn("recipe_name", prompt)
        self.assertIn("meal_type", prompt)
        self.assertIn("day", prompt)

    def test_build_meal_plan_prompt_contains_rules(self):
        """Prompt should contain the meal planning rules."""
        prompt = build_meal_plan_prompt("macros", "cuisine", "pantry")
        self.assertIn("meal planning assistant", prompt)
        self.assertIn("21", prompt)
        self.assertIn("7 days", prompt)
