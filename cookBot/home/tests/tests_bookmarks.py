from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from home.models import Recipe
import json


class BookmarkTests(TestCase):
    def setUp(self):
        """Set up test data before each test method"""
        # Create test user
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

        # Create test recipe
        self.recipe = Recipe.objects.create(
            user=self.user, title="Test Recipe", is_public=True
        )

        # URL endpoints
        self.toggle_url = reverse("toggle_favorite", args=[self.recipe.id])
        self.favorites_list_url = reverse("favorites_list")

    def test_toggle_favorite_adds_recipe(self):
        """Test that first POST request adds recipe to user's favorites"""
        self.client.login(username="testuser", password="testpass123")

        # Verify user doesn't have the recipe as favorite initially
        self.assertFalse(self.user.favorite_recipes.filter(id=self.recipe.id).exists())

        # Send POST request to toggle
        response = self.client.post(self.toggle_url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertTrue(data["saved"])
        self.assertEqual(data["recipe_id"], self.recipe.id)

        # Verify recipe was added
        self.assertTrue(self.user.favorite_recipes.filter(id=self.recipe.id).exists())

    def test_toggle_favorite_removes_recipe(self):
        """Test that second POST request removes recipe from user's favorites"""
        self.client.login(username="testuser", password="testpass123")

        # First toggle - add the recipe
        self.client.post(self.toggle_url)
        self.assertTrue(self.user.favorite_recipes.filter(id=self.recipe.id).exists())

        # Second toggle - remove the recipe
        response = self.client.post(self.toggle_url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertFalse(data["saved"])
        self.assertEqual(data["recipe_id"], self.recipe.id)

        # Verify recipe was removed
        self.assertFalse(self.user.favorite_recipes.filter(id=self.recipe.id).exists())

    def test_toggle_favorite_requires_authentication(self):
        """Test that unauthenticated users are blocked from toggling favorites"""
        # Try without logging in
        response = self.client.post(self.toggle_url)

        # Should redirect to login page or return 403/302
        self.assertIn(
            response.status_code, [status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN]
        )

        # Verify recipe wasn't added
        self.assertFalse(self.user.favorite_recipes.filter(id=self.recipe.id).exists())

    def test_favorites_list_only_returns_user_bookmarks(self):
        """Test that favorites list view only shows recipes the current user has bookmarked"""
        self.client.login(username="testuser", password="testpass123")

        # Create second user and second recipe
        other_user = User.objects.create_user(
            username="otheruser", password="otherpass123"
        )
        other_recipe = Recipe.objects.create(
            user=other_user, title="Other Recipe", is_public=True
        )

        # Add only first recipe to our test user's favorites
        self.client.post(self.toggle_url)

        # Get favorites list
        response = self.client.get(self.favorites_list_url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify only the bookmarked recipe appears in the list
        content = response.content.decode()
        self.assertIn(self.recipe.title, content)
        self.assertNotIn(other_recipe.title, content)

    def test_toggle_favorite_json_response_format(self):
        """Test that view returns correctly formatted JSON response"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(self.toggle_url)

        # Verify JSON headers
        self.assertEqual(response["Content-Type"], "application/json")

        # Verify JSON structure
        data = json.loads(response.content)
        self.assertIn("saved", data)
        self.assertIn("recipe_id", data)
        self.assertIsInstance(data["saved"], bool)
        self.assertEqual(data["recipe_id"], self.recipe.id)
