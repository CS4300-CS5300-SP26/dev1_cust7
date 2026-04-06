from behave import given, when, then
from django.urls import reverse

@given('another user exists with email "{email}"')
def step_other_user_exists(context, email):
    from django.contrib.auth.models import User

    User.objects.filter(username='otheruser').delete()
    User.objects.filter(email__iexact=email).delete()
    User.objects.create_user(
        username='otheruser',
        email=email,
        password='testpass123'
    )


@when('I submit valid account changes')
def step_submit_valid_account_changes(context):
    context.response = context.client.post(reverse('edit_account'), {
        'first_name': 'Updated',
        'last_name': 'User',
        'username': 'testuser',
        'email': 'updated@email.com',
    })


@when('I submit account changes with email "{email}"')
def step_submit_account_changes_duplicate_email(context, email):
    context.response = context.client.post(reverse('edit_account'), {
        'first_name': 'Updated',
        'last_name': 'User',
        'username': 'testuser',
        'email': email,
    })


@then('the account update should succeed')
def step_account_update_succeeds(context):
    assert context.response.status_code == 302


@then('my first name should be updated')
def step_first_name_updated(context):
    from django.contrib.auth.models import User

    user = User.objects.get(username='testuser')
    assert user.first_name == 'Updated'


@then('my email should be updated')
def step_email_updated(context):
    from django.contrib.auth.models import User

    user = User.objects.get(username='testuser')
    assert user.email == 'updated@email.com'


@then('the account update should fail')
def step_account_update_fails(context):
    assert context.response.status_code == 200


@then('I should see the email already in use error')
def step_email_in_use_error(context):
    content = context.response.content.decode()
    assert "That email is already in use." in content