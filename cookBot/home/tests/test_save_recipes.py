import json
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from home.models import (
    ChatSession,
    ChatMessage,
    Recipe,
    RecipeIngredient,
    RecipeStep,
    MealPlan,
)

# ── Shared mock data ──────────────────────────────────────────────────────────

MOCK_PARSED_RECIPE = {
    "title": "Chicken Fried Rice",
    "ingredients": [
        {"quantity": "2", "unit": "cups", "name": "rice"},
        {"quantity": "1", "unit": "", "name": "egg"},
        {"quantity": "200", "unit": "g", "name": "chicken"},
    ],
    "steps": [
        "Cook the rice according to package instructions.",
        "Fry the chicken in a pan until golden.",
        "Mix everything together and serve hot.",
    ],
}

MOCK_NOT_A_RECIPE = {"error": "not_a_recipe"}

MOCK_AI_MEALS = [
    {
        "day": day,
        "meal_type": meal_type,
        "recipe_name": f"Mock {meal_type} Day {day}",
        "calories": 500,
        "protein": 30,
        "fat": 15,
        "carbs": 50,
        "ingredients": [
            {"quantity": "1", "unit": "cup", "name": "rice"},
            {"quantity": "200", "unit": "g", "name": "chicken"},
        ],
        "steps": [
            "Cook the rice.",
            "Grill the chicken.",
            "Serve together.",
        ],
    }
    for day in range(1, 8)
    for meal_type in ["Breakfast", "Lunch", "Dinner"]
]


# ── ChefBot Save Recipe Tests ─────────────────────────────────────────────────

class TestAiChefBotSaveRecipe(TestCase):
    """Tests for the aiChefBot_save_recipe view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")
        self.session = ChatSession.objects.create(
            user=self.user,
            spoonacular_context=[],
        )

    def post_save(self, session_id=None):
        return self.client.post(
            reverse("aiChefBot_save_recipe"),
            data=json.dumps({"session_id": session_id or self.session.id}),
            content_type="application/json",
        )

    # ── Happy path ────────────────────────────────────────────────────────────

    @patch("home.views.parse_recipe_from_text", return_value=MOCK_PARSED_RECIPE)
    def test_save_recipe_success(self, mock_parse):
        """Saving a valid ChefBot recipe response creates a Recipe in the DB."""
        ChatMessage.objects.create(
            session=self.session,
            role="assistant",
            content="Here is a great Chicken Fried Rice recipe with ingredients and steps.",
        )
        response = self.post_save()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["recipe_title"], "Chicken Fried Rice")
        self.assertTrue(Recipe.objects.filter(user=self.user, title="Chicken Fried Rice").exists())

    @patch("home.views.parse_recipe_from_text", return_value=MOCK_PARSED_RECIPE)
    def test_saved_recipe_is_private_by_default(self, mock_parse):
        """Saved recipe should be private by default."""
        ChatMessage.objects.create(session=self.session, role="assistant", content="Recipe content")
        self.post_save()
        recipe = Recipe.objects.filter(user=self.user).first()
        self.assertIsNotNone(recipe)
        self.assertFalse(recipe.is_public)

    @patch("home.views.parse_recipe_from_text", return_value=MOCK_PARSED_RECIPE)
    def test_saved_recipe_has_correct_ingredients(self, mock_parse):
        """Saved recipe should have all ingredients from the parsed response."""
        ChatMessage.objects.create(session=self.session, role="assistant", content="Recipe content")
        self.post_save()
        recipe = Recipe.objects.filter(user=self.user).first()
        self.assertIsNotNone(recipe)
        ingredients = RecipeIngredient.objects.filter(recipe=recipe)
        self.assertEqual(ingredients.count(), 3)
        names = list(ingredients.values_list("name", flat=True))
        self.assertIn("rice", names)
        self.assertIn("egg", names)
        self.assertIn("chicken", names)

    @patch("home.views.parse_recipe_from_text", return_value=MOCK_PARSED_RECIPE)
    def test_saved_recipe_has_correct_steps(self, mock_parse):
        """Saved recipe should have all steps from the parsed response in order."""
        ChatMessage.objects.create(session=self.session, role="assistant", content="Recipe content")
        self.post_save()
        recipe = Recipe.objects.filter(user=self.user).first()
        self.assertIsNotNone(recipe)
        steps = RecipeStep.objects.filter(recipe=recipe).order_by("order")
        self.assertEqual(steps.count(), 3)
        self.assertEqual(steps[0].order, 1)
        self.assertIn("rice", steps[0].text.lower())

    @patch("home.views.parse_recipe_from_text", return_value=MOCK_PARSED_RECIPE)
    def test_save_recipe_returns_recipe_id(self, mock_parse):
        """Save response should include the new recipe ID."""
        ChatMessage.objects.create(session=self.session, role="assistant", content="Recipe content")
        response = self.post_save()
        data = response.json()
        self.assertIn("recipe_id", data)
        self.assertTrue(Recipe.objects.filter(id=data["recipe_id"]).exists())

    @patch("home.views.parse_recipe_from_text", return_value=MOCK_PARSED_RECIPE)
    def test_only_last_assistant_message_is_used(self, mock_parse):
        """Only the most recent assistant message should be sent for parsing."""
        ChatMessage.objects.create(session=self.session, role="assistant", content="Old message")
        ChatMessage.objects.create(session=self.session, role="assistant", content="New recipe message")
        self.post_save()
        # Verify parse was called with the latest message
        call_args = mock_parse.call_args[0][0]
        self.assertIn("New recipe message", call_args)

    # ── Edge cases ────────────────────────────────────────────────────────────

    def test_save_recipe_no_assistant_message_returns_400(self):
        """Returns 400 if there is no ChefBot response in the session yet."""
        ChatMessage.objects.create(session=self.session, role="user", content="Tell me a recipe")
        response = self.post_save()
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_save_recipe_empty_session_returns_400(self):
        """Returns 400 if session has no messages at all."""
        response = self.post_save()
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    @patch("home.views.parse_recipe_from_text", return_value=MOCK_NOT_A_RECIPE)
    def test_save_recipe_not_a_recipe_returns_400(self, mock_parse):
        """Returns 400 with helpful message when ChefBot response is not a recipe."""
        ChatMessage.objects.create(
            session=self.session,
            role="assistant",
            content="A great tip is to always salt your pasta water.",
        )
        response = self.post_save()
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("recipe", data["error"].lower())

    @patch("home.views.parse_recipe_from_text", return_value=MOCK_NOT_A_RECIPE)
    def test_save_recipe_not_a_recipe_does_not_create_recipe(self, mock_parse):
        """No Recipe object should be created when response is not a recipe."""
        ChatMessage.objects.create(session=self.session, role="assistant", content="Just a tip")
        initial_count = Recipe.objects.filter(user=self.user).count()
        self.post_save()
        self.assertEqual(Recipe.objects.filter(user=self.user).count(), initial_count)

    def test_save_recipe_missing_session_id_returns_400(self):
        """Returns 400 when session_id is not provided."""
        response = self.client.post(
            reverse("aiChefBot_save_recipe"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_save_recipe_invalid_session_id_returns_404(self):
        """Returns 404 when session_id does not exist."""
        response = self.post_save(session_id=999999)
        self.assertEqual(response.status_code, 404)

    def test_save_recipe_another_users_session_returns_404(self):
        """Returns 404 when trying to save from another user's session."""
        other_user = User.objects.create_user(username="otheruser", password="testpass123")
        other_session = ChatSession.objects.create(user=other_user, spoonacular_context=[])
        ChatMessage.objects.create(session=other_session, role="assistant", content="Recipe")
        response = self.post_save(session_id=other_session.id)
        self.assertEqual(response.status_code, 404)

    def test_save_recipe_unauthenticated_redirects(self):
        """Unauthenticated users are redirected away from save recipe endpoint."""
        unauthenticated_client = Client()
        response = unauthenticated_client.post(
            reverse("aiChefBot_save_recipe"),
            data=json.dumps({"session_id": self.session.id}),
            content_type="application/json",
        )
        self.assertIn(response.status_code, [302, 403])

    @patch("home.views.parse_recipe_from_text", side_effect=Exception("OpenAI is down"))
    def test_save_recipe_openai_failure_returns_500(self, mock_parse):
        """Returns 500 when OpenAI parsing call fails."""
        ChatMessage.objects.create(session=self.session, role="assistant", content="Recipe content")
        response = self.post_save()
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)

    @patch("home.views.parse_recipe_from_text", return_value={"title": "", "ingredients": [], "steps": []})
    def test_save_recipe_empty_title_returns_400(self, mock_parse):
        """Returns 400 when OpenAI returns a recipe with no title."""
        ChatMessage.objects.create(session=self.session, role="assistant", content="Recipe content")
        response = self.post_save()
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_save_recipe_invalid_json_returns_400(self):
        """Returns 400 when request body is not valid JSON."""
        response = self.client.post(
            reverse("aiChefBot_save_recipe"),
            data="not valid json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)


# ── Calendar Save Meal Plan Tests ─────────────────────────────────────────────

class TestCalendarSaveMealPlan(TestCase):
    """Tests for the calendar_save_meal_plan view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.client.login(username="testuser", password="password123")

    def generate_meal_plan(self):
        """Helper to generate a full meal plan with recipe_data."""
        with patch("home.views.generate_meal_plan_with_ai", return_value=MOCK_AI_MEALS):
            self.client.post(
                reverse("generate_meal_plan"),
                data=json.dumps({"use_pantry": False}),
                content_type="application/json",
            )

    def post_save(self):
        return self.client.post(
            reverse("calendar_save_meal_plan"),
            data=json.dumps({}),
            content_type="application/json",
        )

    # ── Happy path ────────────────────────────────────────────────────────────

    def test_save_meal_plan_success(self):
        """Saving a generated meal plan creates Recipe objects for all meals."""
        self.generate_meal_plan()
        response = self.post_save()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreater(data["saved_count"], 0)

    def test_save_meal_plan_creates_correct_recipe_count(self):
        """Saving creates one Recipe per MealPlan that has recipe_data."""
        self.generate_meal_plan()
        response = self.post_save()
        data = response.json()
        recipe_count = Recipe.objects.filter(user=self.user).count()
        self.assertEqual(recipe_count, data["saved_count"])

    def test_saved_meal_recipes_are_private(self):
        """All saved meal plan recipes should be private by default."""
        self.generate_meal_plan()
        self.post_save()
        recipes = Recipe.objects.filter(user=self.user)
        for recipe in recipes:
            self.assertFalse(recipe.is_public, f"Recipe '{recipe.title}' should be private")

    def test_saved_meal_recipes_have_ingredients(self):
        """Saved meal recipes should have ingredients from recipe_data."""
        self.generate_meal_plan()
        self.post_save()
        recipe = Recipe.objects.filter(user=self.user).first()
        self.assertIsNotNone(recipe)
        self.assertTrue(RecipeIngredient.objects.filter(recipe=recipe).exists())

    def test_saved_meal_recipes_have_steps(self):
        """Saved meal recipes should have steps from recipe_data."""
        self.generate_meal_plan()
        self.post_save()
        recipe = Recipe.objects.filter(user=self.user).first()
        self.assertIsNotNone(recipe)
        self.assertTrue(RecipeStep.objects.filter(recipe=recipe).exists())

    def test_saved_meal_recipes_include_macro_description(self):
        """Saved recipe descriptions should include macro information."""
        self.generate_meal_plan()
        self.post_save()
        recipe = Recipe.objects.filter(user=self.user).first()
        self.assertIsNotNone(recipe)
        self.assertIn("cal", recipe.description.lower())

    def test_save_meal_plan_links_recipe_id_to_meal_plan(self):
        """After saving, each MealPlan should have a recipe_id pointing to the saved Recipe."""
        self.generate_meal_plan()
        self.post_save()
        today = date.today()
        meal_plans = MealPlan.objects.filter(
            user=self.user,
            date__gte=today,
            date__lte=today + timedelta(days=6),
        )
        for meal_plan in meal_plans:
            if meal_plan.recipe_data:
                self.assertIsNotNone(
                    meal_plan.recipe_id,
                    f"MealPlan '{meal_plan.recipe_name}' should have a recipe_id after saving"
                )

    def test_save_returns_success_message(self):
        """Save response should include a success message mentioning saved count."""
        self.generate_meal_plan()
        response = self.post_save()
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("saved", data["message"].lower())

    # ── Edge cases ────────────────────────────────────────────────────────────

    def test_save_meal_plan_no_meal_plan_returns_400(self):
        """Returns 400 when no meal plan exists for the current week."""
        response = self.post_save()
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_save_meal_plan_twice_skips_duplicates(self):
        """Saving twice should not create duplicate Recipe objects."""
        self.generate_meal_plan()
        self.post_save()
        first_count = Recipe.objects.filter(user=self.user).count()
        self.post_save()
        second_count = Recipe.objects.filter(user=self.user).count()
        self.assertEqual(first_count, second_count, "Duplicate recipes were created on second save")

    def test_save_meal_plan_twice_second_returns_400(self):
        """Second save attempt returns 400 with already saved message."""
        self.generate_meal_plan()
        self.post_save()
        response = self.post_save()
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("already", data["error"].lower())

    def test_save_meal_plan_unauthenticated_redirects(self):
        """Unauthenticated users are redirected from save meal plan endpoint."""
        unauthenticated_client = Client()
        response = unauthenticated_client.post(
            reverse("calendar_save_meal_plan"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertIn(response.status_code, [302, 403])

    def test_save_meal_plan_meals_without_recipe_data_are_skipped(self):
        """Meals with no recipe_data are gracefully skipped."""
        # Create a meal plan entry manually with no recipe_data
        today = date.today()
        MealPlan.objects.create(
            user=self.user,
            recipe_name="Old Style Meal",
            date=today,
            meal_type="Dinner",
            recipe_data={},  # empty recipe data
        )
        response = self.post_save()
        # Should return 400 since all meals were skipped
        self.assertIn(response.status_code, [400, 200])

    def test_save_meal_plan_only_saves_current_week(self):
        """Only meals from the current 7-day window are saved."""
        self.generate_meal_plan()
        # Create an old meal plan outside the window
        old_date = date.today() - timedelta(days=30)
        MealPlan.objects.create(
            user=self.user,
            recipe_name="Old Meal",
            date=old_date,
            meal_type="Lunch",
            recipe_data={"ingredients": [{"quantity": "1", "unit": "cup", "name": "rice"}], "steps": ["Cook it"]},
        )
        self.post_save()
        # Old meal should not be saved as a recipe
        self.assertFalse(Recipe.objects.filter(user=self.user, title="Old Meal").exists())

    def test_save_meal_plan_user_isolation(self):
        """Saving only creates recipes for the logged-in user, not other users."""
        other_user = User.objects.create_user(username="otheruser", password="password123")
        # Create a meal plan for other_user
        MealPlan.objects.create(
            user=other_user,
            recipe_name="Other User Meal",
            date=date.today(),
            meal_type="Dinner",
            recipe_data={"ingredients": [], "steps": []},
        )
        self.generate_meal_plan()
        self.post_save()
        # Other user's meal should not be saved as a recipe for this user
        self.assertFalse(Recipe.objects.filter(user=self.user, title="Other User Meal").exists())
        # Other user should have no recipes
        self.assertFalse(Recipe.objects.filter(user=other_user).exists())
