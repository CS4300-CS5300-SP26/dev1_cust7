from behave import given, when, then
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from home.models import Recipe
 
 
@given('a logged in user exists')
def step_logged_in_user_exists(context):
    User.objects.filter(username='testuser').delete()
    context.user = User.objects.create_user(username='testuser', password='testpass123')
    context.client = Client()
    context.client.login(username='testuser', password='testpass123')
 
 
@given('a logged out user')
def step_logged_out_user(context):
    context.client = Client()
 
 
@when('I create a public recipe')
def step_create_public_recipe(context):
    context.recipe = Recipe.objects.create(
        user=context.user,
        title='My Public Pasta',
        is_public=True
    )
 
 
@when('I create a private recipe')
def step_create_private_recipe(context):
    context.recipe = Recipe.objects.create(
        user=context.user,
        title='Secret Stew',
        is_public=False
    )
 
 
@when('I create a private recipe and then make it public')
def step_create_private_then_public(context):
    context.recipe = Recipe.objects.create(
        user=context.user,
        title='Soon Public',
        is_public=False
    )
    context.recipe.is_public = True
    context.recipe.save()
 
 
@when('I create a public recipe and then make it private')
def step_create_public_then_private(context):
    context.recipe = Recipe.objects.create(
        user=context.user,
        title='Going Private',
        is_public=True
    )
    context.recipe.is_public = False
    context.recipe.save()
 
 
@when('I visit the social feed page')
def step_visit_social_feed(context):
    context.response = context.client.get(reverse('social_feed'))
 
 
@when('two different users share a recipe each')
def step_two_users_share_recipes(context):
    User.objects.filter(username='otheruser').delete()
    other_user = User.objects.create_user(username='otheruser', password='testpass123')
    context.recipe1 = Recipe.objects.create(user=context.user, title='My Public Recipe', is_public=True)
    context.recipe2 = Recipe.objects.create(user=other_user, title='Their Public Recipe', is_public=True)
    context.response = context.client.get(reverse('social_feed'))
 
 
@when('I visit the social feed page with multiple public recipes')
def step_visit_feed_with_multiple_recipes(context):
    Recipe.objects.create(user=context.user, title='Older Recipe', is_public=True)
    Recipe.objects.create(user=context.user, title='Newer Recipe', is_public=True)
    context.response = context.client.get(reverse('social_feed'))
 
 
@when('no public recipes exist')
def step_no_public_recipes(context):
    Recipe.objects.filter(is_public=True).delete()
    context.response = context.client.get(reverse('social_feed'))
 
 
@when('a public recipe exists in the feed')
def step_public_recipe_in_feed(context):
    context.recipe = Recipe.objects.create(
        user=context.user,
        title='Linkable Recipe',
        is_public=True
    )
    context.response = context.client.get(reverse('social_feed'))
 
 
@then('the recipe should appear in the social feed')
def step_recipe_in_feed(context):
    response = context.client.get(reverse('social_feed'))
    assert context.recipe.title in response.content.decode()
 
 
@then('the recipe should not appear in the social feed')
def step_recipe_not_in_feed(context):
    response = context.client.get(reverse('social_feed'))
    assert context.recipe.title not in response.content.decode()
 
 
@then('I should be redirected')
def step_redirected(context):
    assert context.response.status_code == 302
 
 
@then('both recipes should appear in the social feed')
def step_both_recipes_in_feed(context):
    content = context.response.content.decode()
    assert context.recipe1.title in content
    assert context.recipe2.title in content
 
 
@then('the recipes should be ordered newest first')
def step_ordered_newest_first(context):
    assert context.response.status_code == 200
    content = context.response.content.decode('utf-8')
    first_pos  = content.find('Newer Recipe')
    second_pos = content.find('Older Recipe')
    assert first_pos < second_pos, "Newer recipe should appear before older recipe in feed"
 
@then('the feed should contain no recipes')
def step_feed_empty(context):
    assert context.response.status_code == 200
    content = context.response.content.decode('utf-8')
    assert 'feed-empty' in content, "Expected empty state div to be present"
    
 
@then("the feed should link to that recipe's page")
def step_feed_links_to_recipe(context):
    expected_url = reverse('recipe_view', args=[context.recipe.id])
    assert expected_url in context.response.content.decode()
 