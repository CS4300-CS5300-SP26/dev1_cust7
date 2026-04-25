from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from home.models import MealPlan


class MealPlanHistoryViewTests(TestCase):
    """Tests for the Meal Plan History view."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )

    def test_history_view_requires_login(self):
        """The history view should redirect or forbid anonymous users."""
        response = self.client.get(reverse("meal_plan_history"))
        self.assertIn(response.status_code, [302, 403])

    def test_user_can_only_see_own_history(self):
        """A user must not see meal plans belonging to another user."""
        user_a = User.objects.create_user(username="userA", password="password123")
        user_b = User.objects.create_user(username="userB", password="password123")

        MealPlan.objects.create(
            user=user_a,
            recipe_name="User A Meal",
            recipe_id=101,
            date=date(2026, 4, 1),
            meal_type="Dinner",
        )
        MealPlan.objects.create(
            user=user_b,
            recipe_name="User B Meal",
            recipe_id=102,
            date=date(2026, 4, 2),
            meal_type="Lunch",
        )

        self.client.login(username="userB", password="password123")
        response = self.client.get(reverse("meal_plan_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User B Meal")
        self.assertNotContains(response, "User A Meal")

    def test_history_view_uses_prefetch_related(self):
        """The view should avoid N+1 queries by prefetching related recipes."""
        for i in range(3):
            MealPlan.objects.create(
                user=self.user,
                recipe_name=f"Meal {i}",
                recipe_id=100 + i,
                date=date(2026, 4, 1 + i),
                meal_type="Breakfast",
            )

        self.client.login(username="testuser", password="password123")
        with self.assertNumQueries(4):
            response = self.client.get(reverse("meal_plan_history"))
        self.assertEqual(response.status_code, 200)
