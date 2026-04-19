from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from home.models import Recipe, RecipeIngredient, RecipeStep, Tag, RecipeTag


class RecipeViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='password123')

    def test_recipe_view_status(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Test Recipe",
            is_public=True
        )
        response = self.client.get(reverse('recipe_view', args=[recipe.id]))
        self.assertEqual(response.status_code, 200)

    def test_recipe_view_steps_ordering(self):
        recipe = Recipe.objects.create(user=self.user, title="Test", is_public=True)
        RecipeStep.objects.create(recipe=recipe, order=2, text="Step 2")
        RecipeStep.objects.create(recipe=recipe, order=1, text="Step 1")

        response = self.client.get(reverse('recipe_view', args=[recipe.id]))
        self.assertEqual(response.context["steps_json"], ["Step 1", "Step 2"])

    def test_recipe_view_ingredients_format(self):
        recipe = Recipe.objects.create(user=self.user, title="Test", is_public=True)
        RecipeIngredient.objects.create(recipe=recipe, quantity="1", unit="cup", name="Flour")
        RecipeIngredient.objects.create(recipe=recipe, quantity="2", unit="", name="Eggs")

        response = self.client.get(reverse('recipe_view', args=[recipe.id]))
        displays = [i['display'] for i in response.context["ingredients_json"]]

        self.assertIn("1 cup Flour", displays)
        self.assertIn("2 Eggs", displays)

    def test_recipe_view_404(self):
        response = self.client.get(reverse('recipe_view', args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_private_recipe_blocked_for_other_user(self):
        recipe = Recipe.objects.create(user=self.user, title='Private', is_public=False)

        other = User.objects.create_user(username='other', password='pass')
        self.client.login(username='other', password='pass')

        response = self.client.get(reverse('recipe_view', args=[recipe.id]))
        self.assertEqual(response.status_code, 403)

    def test_private_recipe_blocked_for_unauthenticated(self):
        recipe = Recipe.objects.create(user=self.user, title='Private', is_public=False)
        self.client.logout()

        response = self.client.get(reverse('recipe_view', args=[recipe.id]))
        self.assertEqual(response.status_code, 403)

    def test_pantry_highlighting(self):
        recipe = Recipe.objects.create(user=self.user, title="Test", is_public=True)
        RecipeIngredient.objects.create(recipe=recipe, name="Flour")

        self.user.pantry_items.create(ingredient_name="flour")

        response = self.client.get(reverse('recipe_view', args=[recipe.id]))
        self.assertIn("flour", response.context["pantry_names_json"])

class CreateRecipeTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.client = Client()

    def test_requires_login(self):
        response = self.client.get(reverse('create_recipe'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/signin', response.url)

    def test_get_request(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('create_recipe'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("grouped_tags", response.context)

    def test_create_recipe_success(self):
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
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertEqual(recipe.steps.count(), 2)

    def test_create_recipe_with_tags(self):
        self.client.login(username='testuser', password='password123')

        tag1, _ = Tag.objects.get_or_create(name="Italian", tag_type="cuisine")
        tag2, _ = Tag.objects.get_or_create(name="Dinner", tag_type="meal")

        self.client.post(reverse('create_recipe'), {
            "title": "Tagged Recipe",
            "tags[]": [str(tag1.id), str(tag2.id)],
            "ingredient_quantity[]": ["1"],
            "ingredient_unit[]": ["cup"],
            "ingredient_name[]": ["Flour"],
            "steps[]": ["Mix"]
        })

        recipe = Recipe.objects.get(title="Tagged Recipe")
        self.assertEqual(RecipeTag.objects.filter(recipe=recipe).count(), 2)

    def test_ignores_empty_fields(self):
        self.client.login(username='testuser', password='password123')

        self.client.post(reverse('create_recipe'), {
            "title": "Edge",
            "ingredient_quantity[]": ["1", ""],
            "ingredient_unit[]": ["cup", ""],
            "ingredient_name[]": ["Flour", "   "],
            "steps[]": ["Step 1", "   "]
        })

        recipe = Recipe.objects.get(title="Edge")
        self.assertEqual(recipe.ingredients.count(), 1)
        self.assertEqual(recipe.steps.count(), 1)

    def test_empty_title_validation(self):
        self.client.login(username='testuser', password='password123')

        response = self.client.post(reverse('create_recipe'), {
            "title": ""
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.context)

class EditRecipeTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='password123')

    def test_edit_recipe_updates_data(self):
        recipe = Recipe.objects.create(user=self.user, title="Old", is_public=False)
        tag, _ = Tag.objects.get_or_create(name="Vegan", tag_type="dietary")

        self.client.post(reverse('edit_recipe', args=[recipe.id]), {
            "title": "Updated",
            "is_public": "on",
            "ingredient_quantity[]": ["2"],
            "ingredient_unit[]": ["cup"],
            "ingredient_name[]": ["Sugar"],
            "steps[]": ["Cook"],
            "tags[]": [str(tag.id)]
        })

        recipe.refresh_from_db()

        self.assertEqual(recipe.title, "Updated")
        self.assertTrue(recipe.is_public)
        self.assertEqual(recipe.ingredients.count(), 1)
        self.assertEqual(recipe.steps.count(), 1)
        self.assertEqual(recipe.tags.count(), 1)

    def test_validation_preserves_data(self):
        recipe = Recipe.objects.create(user=self.user, title="Old", is_public=True)

        response = self.client.post(reverse('edit_recipe', args=[recipe.id]), {
            "title": "",
            "ingredient_quantity[]": ["1"],
            "ingredient_unit[]": ["cup"],
            "ingredient_name[]": ["Flour"],
            "steps[]": ["Mix"]
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("ingredients_data", response.context)
        self.assertIn("steps_data", response.context)

    def test_permission_denied(self):
        recipe = Recipe.objects.create(user=self.user, title="Test", is_public=True)

        other = User.objects.create_user(username='other', password='pass')
        self.client.login(username='other', password='pass')

        response = self.client.get(reverse('edit_recipe', args=[recipe.id]))
        self.assertEqual(response.status_code, 403)

class DeleteRecipeTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='password123')

    def test_delete_recipe(self):
        recipe = Recipe.objects.create(user=self.user, title="Delete Me", is_public=True)

        response = self.client.post(reverse('delete_recipe', args=[recipe.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_permission_denied(self):
        recipe = Recipe.objects.create(user=self.user, title="Test", is_public=True)

        other = User.objects.create_user(username='other', password='pass')
        self.client.login(username='other', password='pass')

        response = self.client.post(reverse('delete_recipe', args=[recipe.id]))
        self.assertEqual(response.status_code, 403)
