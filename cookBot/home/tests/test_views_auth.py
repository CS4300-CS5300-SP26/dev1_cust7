from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from home.forms import RegisterForm, EditProfileForm


class RegisterFormTests(TestCase):

    def test_register_form_rejects_duplicate_email(self):
        User.objects.create_user(
            username="existinguser",
            email="test@email.com",
            password="testpass123"
        )
        form = RegisterForm(data={
            "first_name": "Another",
            "last_name": "User",
            "username": "anotheruser",
            "email": "test@email.com",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn(
            "An account with this email already exists.",
            form.errors["email"]
        )


class EditProfileFormTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@email.com",
            password="testpass123"
        )

    def test_edit_profile_form_rejects_duplicate_email(self):
        User.objects.create_user(
            username="otheruser",
            email="taken@email.com",
            password="testpass123"
        )
        form = EditProfileForm(
            data={
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "email": "taken@email.com",
            },
            instance=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn(
            "That email is already in use.",
            form.errors["email"]
        )


class AccountViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@email.com",
            password="testpass123"
        )

    def test_register_view_creates_user(self):
        response = self.client.post(reverse("register"), {
            "first_name": "New",
            "last_name": "User",
            "username": "newuser",
            "email": "newuser@email.com",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_edit_account_updates_user(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("edit_account"), {
            "first_name": "Updated",
            "last_name": "User",
            "username": "testuser",
            "email": "updated@email.com",
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.email, "updated@email.com")

    def test_change_password_works(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("change_password"), {
            "old_password": "testpass123",
            "new_password1": "NewStrongPassword123!",
            "new_password2": "NewStrongPassword123!",
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPassword123!"))

    def test_change_password_fails_with_wrong_current_password(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("change_password"), {
            "old_password": "wrongpassword",
            "new_password1": "NewStrongPassword123!",
            "new_password2": "NewStrongPassword123!",
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("testpass123"))

    # ---- GET request tests ----

    def test_register_get(self):
        """Test register page loads with GET"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_signin_get(self):
        """Test signin page loads with GET"""
        response = self.client.get(reverse('signin'))
        self.assertEqual(response.status_code, 200)

    def test_signin_successful(self):
        """Test successful signin redirects to index"""
        response = self.client.post(reverse('signin'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('index'))

    def test_account_view(self):
        """Test account page loads for logged-in user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('account'))
        self.assertEqual(response.status_code, 200)

    def test_edit_account_get(self):
        """Test edit_account page loads with GET"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('edit_account'))
        self.assertEqual(response.status_code, 200)

    def test_change_password_get(self):
        """Test change_password page loads with GET"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('change_password'))
        self.assertEqual(response.status_code, 200)

    # ---- Validation error tests ----

    def test_register_form_validation_errors(self):
        """Test views.py lines 72-82: Form validation errors in register view"""
        response = self.client.post(reverse('register'), {
            'username': 'testuser',  # Already exists
            'password1': 'password123',
            'password2': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_register_form_invalid_data(self):
        """Test views.py lines 77-78, 82: Form validation with invalid data"""
        response = self.client.post(reverse('register'), {
            'username': 'test@user!',
            'password1': '123',
            'password2': '456'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertTrue(len(form.errors) > 0)

    def test_signin_invalid_credentials(self):
        """Test views.py line 103: Invalid username/password in signin"""
        response = self.client.post(reverse('signin'), {
            'username': 'nonexistent',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

    def test_edit_account_invalid_form(self):
        """Test edit_account when form is invalid (duplicate email)"""
        User.objects.create_user(username='otheruser', email='taken@email.com', password='pass123')
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('edit_account'), {
            'first_name': 'Test',
            'last_name': 'User',
            'username': 'testuser',
            'email': 'taken@email.com'
        })
        self.assertEqual(response.status_code, 200)

    def test_change_password_invalid_form(self):
        """Test change_password when form is invalid (wrong current password)"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('change_password'), {
            'old_password': 'wrongpassword',
            'new_password1': 'NewStrongPassword123!',
            'new_password2': 'NewStrongPassword123!'
        })
        self.assertEqual(response.status_code, 200)

    # ---- Unauthorized access tests ----

    def test_edit_account_requires_login(self):
        """Test that edit_account redirects when not logged in"""
        response = self.client.get(reverse('edit_account'))
        self.assertIn(response.status_code, [302, 403])

    def test_account_requires_login(self):
        """Test that account view redirects when not logged in"""
        response = self.client.get(reverse('account'))
        self.assertIn(response.status_code, [302, 403])


class IntegrationTest(TestCase):
    """Full user journey integration test."""

    def setUp(self):
        self.base_user = User.objects.create_user(username='testuser', password='password123')

    @staticmethod
    def _mock_spoonacular():
        from unittest.mock import patch
        return patch('home.views.spoonacular_get')

    def test_full_user_journey(self):
        """Integration test: Register -> Create Recipe -> Add to Pantry -> Generate Meal Plan -> View Calendar -> Logout"""
        from home.models import MealPlan, Pantry, Recipe

        with self._mock_spoonacular() as mock_spoonacular:
            # 1. Register a new user
            response = self.client.post(reverse('register'), {
                'first_name': 'Integration',
                'last_name': 'Test',
                'username': 'integrationuser',
                'email': 'integration@test.com',
                'password1': 'StrongPassword123!',
                'password2': 'StrongPassword123!'
            })
            self.assertEqual(response.status_code, 302)

            # 2. Create a recipe
            response = self.client.post(reverse('create_recipe'), {
                'title': 'Integration Test Recipe',
                'is_public': 'on',
                'ingredient_quantity[]': ['1'],
                'ingredient_unit[]': ['cup'],
                'ingredient_name[]': ['Flour'],
                'steps[]': ['Mix ingredients']
            })
            self.assertEqual(response.status_code, 302)

            # 3. View the recipe
            recipe = Recipe.objects.get(title='Integration Test Recipe')
            response = self.client.get(reverse('recipe_view', args=[recipe.id]))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Integration Test Recipe')

            # 4. Add ingredient to pantry
            import json
            response = self.client.post(
                reverse('add_ingredient'),
                data=json.dumps({'ingredient_name': 'Sugar'}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            integration_user = User.objects.get(username='integrationuser')
            self.assertTrue(Pantry.objects.filter(ingredient_name='Sugar', user=integration_user).exists())

            # 5. Generate meal plan
            mock_spoonacular.return_value = [{'id': i, 'title': f'Recipe {i}'} for i in range(1, 8)]
            response = self.client.post(reverse('generate_meal_plan'))
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])
            self.assertEqual(data['meals_count'], 7)

            # 6. View calendar
            response = self.client.get(reverse('calendar'))
            self.assertEqual(response.status_code, 200)

            # 7. Logout
            response = self.client.get(reverse('logout'))
            self.assertEqual(response.status_code, 302)