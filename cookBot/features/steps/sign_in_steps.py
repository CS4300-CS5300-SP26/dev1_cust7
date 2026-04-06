from behave import given, when, then

@given('a registered user exists')
def step_registered_user_exists(context):
    from django.contrib.auth.models import User

    User.objects.filter(username='testuser').delete()
    User.objects.create_user(username='testuser', password='testpass123')

@given('I am a logged in user')
def step_i_am_logged_in_user(context):
    from django.contrib.auth.models import User
    from django.test import Client

    context.client = Client()

    User.objects.filter(username='testuser').delete()
    User.objects.create_user(username='testuser', password='testpass123')

    response = context.client.post('/signin/', {
        'username': 'testuser',
        'password': 'testpass123',
    })

    assert response.status_code == 302
    assert context.client.session.get('_auth_user_id') is not None

@when('I submit valid sign in credentials')
def step_submit_valid_signin(context):
    from django.test import Client

    context.client = Client()
    context.response = context.client.post('/signin/', {
        'username': 'testuser',
        'password': 'testpass123',
    })

@when('I visit the logout page')
def step_visit_logout(context):
    context.response = context.client.get('/logout/')

@then('I should be redirected to the home page')
def step_redirected_to_home(context):
    assert context.response.status_code == 302
    assert context.response.url == '/'

@then('the user should be authenticated')
def step_user_authenticated(context):
    user_id = context.client.session.get('_auth_user_id')
    assert user_id is not None

@then('the user should not be authenticated')
def step_user_not_authenticated(context):
    user_id = context.client.session.get('_auth_user_id')
    assert user_id is None