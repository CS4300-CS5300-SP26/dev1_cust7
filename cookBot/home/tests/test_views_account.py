from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AccountPageLinkTests(TestCase):
    """Tests for links present on the account page."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="testuser@email.com", password="testpass123"
        )

    def test_account_page_contains_meal_plan_history_link(self):
        """The account page should display a link to the Meal Plan History page near the Security and Change Password sections."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("account"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meal Plan History")
        self.assertContains(response, reverse("meal_plan_history"))
