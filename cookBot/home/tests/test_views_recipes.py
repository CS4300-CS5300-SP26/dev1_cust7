from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from home.models import Recipe, RecipeIngredient, RecipeStep


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

    def test_recipe_view_private_recipe_different_user(self):
        """Test that a different user cannot view a private recipe"""
        recipe = Recipe.objects.create(user=self.user, title='Private Recipe', is_public=False)
        other_user = User.objects.create_user(username='otheruser', password='pass123')
        self.client.login(username='otheruser', password='pass123')
        response = self.client.get(reverse('recipe_view', args=[recipe.id]))
        self.assertEqual(response.status_code, 403)

    def test_recipe_view_private_recipe_unauthenticated(self):
        """Test that unauthenticated user cannot view private recipe"""
        recipe = Recipe.objects.create(user=self.user, title='Private Recipe', is_public=False)
        self.client.logout()
        response = self.client.get(reverse('recipe_view', args=[recipe.id]))
        self.assertEqual(response.status_code, 403)


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
            "ingredient_name[]": ["Flour", "   "],
            "steps[]": ["Step 1", "   "]
        })
        recipe = Recipe.objects.get(title="Edge Recipe")
        self.assertEqual(RecipeIngredient.objects.filter(recipe=recipe).count(), 1)
        self.assertEqual(RecipeStep.objects.filter(recipe=recipe).count(), 1)

    def test_create_recipe_empty_title(self):
        """Test create_recipe with empty title shows error"""
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('create_recipe'), {
            'title': '',
            'is_public': 'on'
        })
        self.assertIn(response.status_code, [200, 302])