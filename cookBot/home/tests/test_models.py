from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from home.models import MealPlan, Recipe, RecipeIngredient, RecipeRating, RecipeStep, Tag, RecipeTag


# https://docs.djangoproject.com/en/6.0/topics/testing/overview/ Reference as needed

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


class MealPlanModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_mealplan_is_created_with_required_fields(self):
        """Given a meal plan is created, it includes all required fields: user, recipe_name, recipe_id, date, and meal_type"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            recipe_name='Spaghetti',
            recipe_id=12345,
            date=date(2026, 4, 3),
            meal_type='Dinner'
        )
        self.assertEqual(meal_plan.user, self.user)
        self.assertEqual(meal_plan.recipe_name, 'Spaghetti')
        self.assertEqual(meal_plan.recipe_id, 12345)
        self.assertEqual(meal_plan.date, date(2026, 4, 3))
        self.assertEqual(meal_plan.meal_type, 'Dinner')

class TagModelTest(TestCase):

    def setUp(self):
        self.tag, _ = Tag.objects.get_or_create(
            name='Vegan',
            defaults={'tag_type': 'dietary', 'description': ''}
        )

    def test_tag_creation(self):
        """Tag is created with correct fields"""
        self.assertEqual(self.tag.name, 'Vegan')
        self.assertEqual(self.tag.tag_type, 'dietary')
        self.assertEqual(self.tag.description, '')

    def test_tag_str(self):
        """Tag __str__ returns correct format"""
        self.assertEqual(str(self.tag), '[dietary] Vegan')

    def test_tag_name_is_unique(self):
        """Creating a tag with a duplicate name raises an error"""
        with self.assertRaises(Exception):
            Tag.objects.create(name='Vegan', tag_type='dietary')

    def test_tag_default_type_is_other(self):
        """Tag defaults to 'other' type when none is provided"""
        tag, _ = Tag.objects.get_or_create(name='One-Pan')
        self.assertEqual(tag.tag_type, 'other')

    def test_tag_ordering(self):
        """Tags are ordered by tag_type then name"""
        Tag.objects.get_or_create(name='Italian', defaults={'tag_type': 'cuisine'})
        Tag.objects.get_or_create(name='Gluten-Free', defaults={'tag_type': 'dietary'})
        tags = list(Tag.objects.all())
        tag_types = [t.tag_type for t in tags]
        self.assertEqual(tag_types, sorted(tag_types))

    def test_all_tag_types_are_valid(self):
        """All TagType choices can be saved to the database"""
        valid_types = ['dietary', 'cuisine', 'cooktime', 'meal', 'other']
        for i, tag_type in enumerate(valid_types):
            tag, _ = Tag.objects.get_or_create(name=f'Test Tag {i}', defaults={'tag_type': tag_type})
            self.assertEqual(tag.tag_type, tag_type)


class RecipeTagTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.recipe = Recipe.objects.create(user=self.user, title='Pasta')
        self.tag, _ = Tag.objects.get_or_create(name='Italian', defaults={'tag_type': 'cuisine'})

    def test_add_tag_to_recipe(self):
        """A tag can be added to a recipe"""
        self.recipe.tags.add(self.tag)
        self.assertIn(self.tag, self.recipe.tags.all())

    def test_recipe_tag_through_model_created(self):
        """Adding a tag creates a RecipeTag row"""
        self.recipe.tags.add(self.tag)
        self.assertTrue(RecipeTag.objects.filter(recipe=self.recipe, tag=self.tag).exists())

    def test_duplicate_tag_on_recipe_raises_error(self):
        """Adding the same tag to a recipe twice raises an error"""
        self.recipe.tags.add(self.tag)
        with self.assertRaises(Exception):
            RecipeTag.objects.create(recipe=self.recipe, tag=self.tag)

    def test_remove_tag_from_recipe(self):
        """A tag can be removed from a recipe"""
        self.recipe.tags.add(self.tag)
        self.recipe.tags.remove(self.tag)
        self.assertNotIn(self.tag, self.recipe.tags.all())

    def test_recipe_can_have_multiple_tags(self):
        """A recipe can have multiple tags"""
        tag2, _ = Tag.objects.get_or_create(name='Vegan', defaults={'tag_type': 'dietary'})
        self.recipe.tags.add(self.tag, tag2)
        self.assertEqual(self.recipe.tags.count(), 2)

    def test_tag_deletion_removes_recipe_tag(self):
        """Deleting a tag removes its RecipeTag entries"""
        self.recipe.tags.add(self.tag)
        self.tag.delete()
        self.assertEqual(RecipeTag.objects.filter(recipe=self.recipe).count(), 0)

    def test_filter_recipes_by_tag(self):
        """Recipes can be filtered by tag"""
        tag2, _ = Tag.objects.get_or_create(name='Vegan', defaults={'tag_type': 'dietary'})
        recipe2 = Recipe.objects.create(user=self.user, title='Salad')
        self.recipe.tags.add(self.tag)
        recipe2.tags.add(tag2)

        results = Recipe.objects.filter(tags__name='Italian')
        self.assertIn(self.recipe, results)
        self.assertNotIn(recipe2, results)
