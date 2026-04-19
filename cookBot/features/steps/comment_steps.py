from behave import given, when, then
from django.urls import reverse
from django.contrib.auth.models import User
from home.models import Recipe, Comment


@given('I am logged in and viewing a recipe')
def step_logged_in_viewing_recipe(context):
    # Create test user
    User.objects.filter(username='comment_user').delete()
    context.user = User.objects.create_user(username='comment_user', password='testpass123')
    
    # Create test recipe
    context.recipe = Recipe.objects.create(
        user=context.user,
        title='Test Recipe for Comments',
        is_public=True
    )
    
    # Log in
    context.client.post(reverse('signin'), {
        'username': 'comment_user',
        'password': 'testpass123',
    })


@when('I submit a comment with text "{comment_text}"')
def step_submit_comment(context, comment_text):
    url = reverse('post_comment', args=[context.recipe.id])
    context.response = context.client.post(url, {
        'text': comment_text
    })


@then('the comment should be saved to the database')
def step_verify_comment_saved(context):
    assert Comment.objects.count() == 1
    context.comment = Comment.objects.first()


@then('the comment should be associated with the recipe')
def step_verify_comment_associated(context):
    assert context.comment.recipe == context.recipe
    assert context.recipe.comments.count() == 1


@then('the comment should be associated with my user account')
def step_verify_comment_owned_by_user(context):
    assert context.comment.user == context.user


@given('I am not logged in')
def step_not_logged_in(context):
    context.client.logout()
    
    # Create test recipe
    context.recipe = Recipe.objects.create(
        user=User.objects.create_user(username='other_user', password='test123'),
        title='Public Recipe',
        is_public=True
    )


@then('no comment should be created')
def step_no_comment_created(context):
    assert Comment.objects.count() == 0