from behave import given, when, then
from django.urls import reverse
from django.contrib.auth.models import User
from home.models import Recipe
import json

@given('I am a logged in user and a recipe exists')
def step_logged_in_user_with_recipe(context):
    # Ensure test user exists
    User.objects.filter(username='bookmark_user').delete()
    context.user = User.objects.create_user(username='bookmark_user', password='testpass123')
    
    # Create a recipe
    context.recipe = Recipe.objects.create(
        user=context.user,
        title='Delicious Bookmark Recipe',
        is_public=True
    )
    
    # Log in (bypasses CSRF and form validation for test setup)
    context.client.force_login(context.user)

@when('I click the bookmark icon for the recipe')
def step_click_bookmark_icon(context):
    url = reverse('toggle_favorite', args=[context.recipe.id])
    context.response = context.client.post(url)

@then('the icon should change state and the recipe is saved')
def step_verify_recipe_saved(context):
    assert context.response.status_code == 200
    data = json.loads(context.response.content)
    assert data['saved'] is True
    assert context.user.favorite_recipes.filter(id=context.recipe.id).exists()

@then('the recipe appears on the "Saved Recipes" page')
def step_verify_recipe_in_list(context):
    url = reverse('favorites_list')
    response = context.client.get(url)
    assert response.status_code == 200
    assert context.recipe.title in response.content.decode()

@when('I click the bookmark icon again')
def step_click_bookmark_icon_again(context):
    url = reverse('toggle_favorite', args=[context.recipe.id])
    context.response = context.client.post(url)

@then('the recipe is removed from the "Saved Recipes" page')
def step_verify_recipe_removed(context):
    # Check JSON response state
    data = json.loads(context.response.content)
    assert data['saved'] is False
    
    # Check DB state
    assert not context.user.favorite_recipes.filter(id=context.recipe.id).exists()
    
    # Check Saved Recipes page
    url = reverse('favorites_list')
    response = context.client.get(url)
    assert context.recipe.title not in response.content.decode()
