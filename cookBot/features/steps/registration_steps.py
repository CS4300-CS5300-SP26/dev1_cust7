from behave import given, when, then

@given('No user exists with username "newuser"')
def step_no_user_exists(context):
      from django.contrib.auth.models import User
      
      User.objects.filter(username='newuser').delete()

@given('no user exists with email "newuser@email.com"')
def step_no_email_exists(context):
      from django.contrib.auth.models import User
      User.objects.filter(email__iexact='newuser@email.com').delete()

@when('I submit valid registration details')
def step_submit_valid_registration(context):
    from django.test import Client

    context.client = Client()
    context.response = context.client.post('/register/', {
        'first_name': 'New',
        'last_name': 'User',
        'username': 'newuser',
        'email': 'newuser@email.com',
        'password1': 'StrongPassword123!',
        'password2': 'StrongPassword123!',
    })

@then('the registration should succeed')
def step_registration_succeeds(context):
    assert context.response.status_code == 302
    
@then('the user should be able to log in')
def step_user_can_log_in(context):
      from django.contrib.auth.models import User
      from django.test import Client
      
      context.client = Client()
      
      response = context.client.post('/signin/', {
            'username': 'newuser',
            'password': 'StrongPassword123!',
      })
      
      assert response.status_code == 302
      assert context.client.session.get('_auth_user_id') is not None

@given('a user exists with email "test@email.com"')
def step_user_exists_with_email(context):
      from django.contrib.auth.models import User
      User.objects.filter(username='existinguser').delete()
      User.objects.filter(email__iexact='test@email.com').delete()
      User.objects.create_user(
            username='existinguser',
            email='test@email.com',
            password='testpass123'
    )
@when('I submit registration details with "test@email.com"')
def step_submit_registration_with_existing_email(context):
      from django.test import Client
      context.client = Client()
      context.response = context.client.post('/register/', {
            'first_name': 'Another',
            'last_name': 'User',
            'username': 'anotheruser',
            'email': 'test@email.com',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
      })
@then('the registration should fail')
def step_registration_fails(context):
      print("STATUS:", context.response.status_code)
      print("BODY:", context.response.content.decode())

      assert context.response.status_code == 200

@then('I should see a duplicate email error')
def step_duplicate_email_error(context):
    content = context.response.content.decode()
    assert "An account with this email already exists." in content
