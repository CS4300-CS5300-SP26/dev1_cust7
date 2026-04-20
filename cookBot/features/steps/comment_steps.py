from behave import given, when, then
from django.urls import reverse
from django.contrib.auth.models import User
from home.models import Recipe, Comment


@given('I am logged in and viewing a recipe')
def step_logged_in_viewing_recipe(context):
    # Create or get test user
    context.user, created = User.objects.get_or_create(
        username='comment_user'
    )
    # Always hash password properly for both new and existing users
    context.user.set_password('testpass123')
    context.user.save()
    
    # Create test recipe
    context.recipe, created = Recipe.objects.get_or_create(
        user=context.user,
        title='Test Recipe for Comments',
        defaults={'is_public': True}
    )
    
    # Log in
    context.client.post(reverse('signin'), {
        'username': 'comment_user',
        'password': 'testpass123',
    })


@when('I submit a comment with text "{comment_text}"')
def step_submit_comment(context, comment_text):
    url = reverse('post_comment', kwargs={'recipe_id': context.recipe.id})
    context.response = context.client.post(url, {
        'text': comment_text
    }, follow=True)


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


@given('I am not logged in and viewing a recipe')
def step_not_logged_in_viewing_recipe(context):
    context.client.logout()
    
    # Create or get test user
    other_user, created = User.objects.get_or_create(
        username='other_user',
        defaults={'password': 'test123'}
    )
    if not created:
        other_user.set_password('test123')
        other_user.save()
    
    # Create test recipe
    context.recipe, created = Recipe.objects.get_or_create(
        user=other_user,
        title='Public Recipe',
        defaults={'is_public': True}
    )


@then('no comment should be created')
def step_no_comment_created(context):
    assert Comment.objects.count() == 0