from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from home.models import UserStreak


class StreakIncrementTests(TestCase):
    """Tests for the increment_streak endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="streakuser", password="streakpass123"
        )
        self.client.login(username="streakuser", password="streakpass123")

    def test_double_click_same_day_only_increments_once(self):
        """Clicking 'Made Recipe' twice on the same day should only increment the streak once."""
        response1 = self.client.post(reverse("increment_streak"))
        self.assertEqual(response1.status_code, 200)
        data1 = response1.json()
        self.assertEqual(data1["current_streak"], 1)

        response2 = self.client.post(reverse("increment_streak"))
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertEqual(data2["current_streak"], 1)

        streak = UserStreak.objects.get(user=self.user)
        self.assertEqual(streak.current_streak, 1)
        self.assertEqual(streak.last_cooked_date, date.today())

    def test_streak_resets_after_missing_a_day(self):
        """If the user misses a day, the streak should reset to 1."""
        streak = UserStreak.objects.create(
            user=self.user,
            current_streak=5,
            longest_streak=5,
            last_cooked_date=date.today() - timedelta(days=2),
        )

        response = self.client.post(reverse("increment_streak"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["current_streak"], 1)

        streak.refresh_from_db()
        self.assertEqual(streak.current_streak, 1)
        self.assertEqual(streak.last_cooked_date, date.today())

    def test_streak_increments_on_consecutive_days(self):
        """Streak should increment when cooking on consecutive days."""
        UserStreak.objects.create(
            user=self.user,
            current_streak=3,
            longest_streak=3,
            last_cooked_date=date.today() - timedelta(days=1),
        )

        response = self.client.post(reverse("increment_streak"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["current_streak"], 4)
        self.assertEqual(data["longest_streak"], 4)

    def test_longest_streak_not_overwritten(self):
        """Longest streak should not decrease if current streak is lower."""
        UserStreak.objects.create(
            user=self.user,
            current_streak=10,
            longest_streak=10,
            last_cooked_date=date.today() - timedelta(days=3),
        )

        response = self.client.post(reverse("increment_streak"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["current_streak"], 1)
        self.assertEqual(data["longest_streak"], 10)


class StreakResetTests(TestCase):
    """Tests for the reset_streak endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="resetuser", password="resetpass123"
        )
        self.client.login(username="resetuser", password="resetpass123")

    def test_user_can_reset_streak(self):
        """A POST to reset_streak should set current_streak to 0 and clear last_cooked_date."""
        UserStreak.objects.create(
            user=self.user,
            current_streak=7,
            longest_streak=7,
            last_cooked_date=date.today(),
        )

        response = self.client.post(reverse("reset_streak"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["current_streak"], 0)

        streak = UserStreak.objects.get(user=self.user)
        self.assertEqual(streak.current_streak, 0)
        self.assertIsNone(streak.last_cooked_date)
        self.assertEqual(streak.longest_streak, 7)
