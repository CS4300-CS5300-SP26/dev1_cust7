from behave import given, when, then
from unittest.mock import patch
import json
from django.contrib.auth.models import User
from django.test import Client
from home.models import ChatSession

#GIVEN
@given('I am not logged in')
def step_not_logged_in(context):
    from django.test import Client
    context.client = Client()
 
 
@given('I am a logged in user with a chat session')
def step_logged_in_with_session(context):
    context.client = Client()
 
    User.objects.filter(username='testuser').delete()
    user = User.objects.create_user(username='testuser', password='testpass123')
 
    context.client.post('/signin/', {
        'username': 'testuser',
        'password': 'testpass123',
    })
 
    # Create a chat session for this user
    context.session = ChatSession.objects.create(
        user=user,
        spoonacular_context=[],
    )

@given('I am a logged in user with saved recipes')
def step_logged_in_with_saved_recipes(context):
    from django.contrib.auth.models import User
    from django.test import Client
    from home.models import Recipe
 
    context.client = Client()
 
    User.objects.filter(username='testuser').delete()
    user = User.objects.create_user(username='testuser', password='testpass123')
 
    context.client.post('/signin/', {
        'username': 'testuser',
        'password': 'testpass123',
    })
 
    # Create two saved recipes for this user
    Recipe.objects.create(user=user, title='Chicken Stir Fry', is_public=False)
    Recipe.objects.create(user=user, title='Pasta Carbonara', is_public=False)
 
@given('I am a logged in user with pantry ingredients')
def step_logged_in_with_pantry(context):
    from django.contrib.auth.models import User
    from django.test import Client
 
    context.client = Client()
 
    User.objects.filter(username='testuser').delete()
    user = User.objects.create_user(username='testuser', password='testpass123')
 
    context.client.post('/signin/', {
        'username': 'testuser',
        'password': 'testpass123',
    })
 
    # Add pantry ingredients for this user
    user.pantry_items.create(ingredient_name='chicken')
    user.pantry_items.create(ingredient_name='rice')

#WHEN
@when('I visit the aiChefBot page')
def step_visit_aichefbot(context):
    context.response = context.client.get('/aiChefBot/')
 
 
@when('I visit the aiChefBot page with mocked Spoonacular')
def step_visit_aichefbot_mocked_spoonacular(context):
    # Mock Spoonacular so we don't make real API calls
    mock_spoonacular_results = [
        {
            'title': 'Chicken Fried Rice',
            'usedIngredients': [{'name': 'chicken'}, {'name': 'rice'}],
            'missedIngredients': [],
        },
        {
            'title': 'Chicken Soup',
            'usedIngredients': [{'name': 'chicken'}],
            'missedIngredients': [{'name': 'broth'}],
        },
    ]
    context.client.session
    user = User.objects.get(username='testuser')
    user.pantry_items.get_or_create(ingredient_name='chicken')

    with patch('home.spoonacular.spoonacular_get', return_value=mock_spoonacular_results):
        context.response = context.client.get('/aiChefBot/')
 
 
@when('I submit an empty message to the chat')
def step_submit_empty_message(context):
    context.response = context.client.post(
        '/aiChefBot/chat/',
        data=json.dumps({'session_id': context.session.id, 'message': ''}),
        content_type='application/json',
    )
 
 
@when('I submit a message with an invalid session ID')
def step_submit_invalid_session(context):
    context.response = context.client.post(
        '/aiChefBot/chat/',
        data=json.dumps({'session_id': 999999, 'message': 'Hello ChefBot'}),
        content_type='application/json',
    )
 
 
@when('the OpenAI API fails')
def step_openai_fails(context):
    context.openai_patch = patch(
        'home.views.call_openai',
        side_effect=Exception('OpenAI is down')
    )
    context.openai_patch.start()
 
 
@when('I send a message')
def step_send_message(context):
    context.response = context.client.post(
        '/aiChefBot/chat/',
        data=json.dumps({'session_id': context.session.id, 'message': 'What can I cook?'}),
        content_type='application/json',
    )
    # Stop the patch after the request is made
    context.openai_patch.stop()

@when('I send a valid message to ChefBot')
def step_send_valid_message(context):
    # Mock call_openai so we don't make a real API call
    with patch('home.views.call_openai', return_value='Here is a great recipe for chicken fried rice!'):
        context.response = context.client.post(
            '/aiChefBot/chat/',
            data=json.dumps({'session_id': context.session.id, 'message': 'What can I make with chicken?'}),
            content_type='application/json',
        )
#THEN        
@then('I should be redirected to the sign in page')
def step_redirected_to_signin(context):
    assert context.response.status_code == 302
    assert '/signin' in context.response.url

 
@then('I should receive a 404 error response')
def step_receive_404(context):
    assert context.response.status_code == 404
    data = json.loads(context.response.content)
    assert 'error' in data
 
 
@then('I should receive a 500 error response')
def step_receive_500(context):
    assert context.response.status_code == 500
    data = json.loads(context.response.content)
    assert 'error' in data
 
 
@then('I should see my saved recipes on the page')
def step_see_saved_recipes(context):
    assert context.response.status_code == 200
    content = context.response.content.decode('utf-8')
    assert 'Chicken Stir Fry' in content
    assert 'Pasta Carbonara' in content
 
 
@then('I should see the Spoonacular suggested recipes on the page')
def step_see_spoonacular_recipes(context):
    assert context.response.status_code == 200
    content = context.response.content.decode('utf-8')
    assert 'Chicken Fried Rice' in content
    assert 'Chicken Soup' in content

@then('I should receive a reply from ChefBot')
def step_receive_reply(context):
    assert context.response.status_code == 200
    data = json.loads(context.response.content)
    assert 'reply' in data
    assert len(data['reply']) > 0
 
@then('the message and reply should be saved to the database')
def step_messages_saved_to_db(context):
    from home.models import ChatMessage
 
    # Check user message was saved
    user_message = ChatMessage.objects.filter(
        session=context.session,
        role='user',
        content='What can I make with chicken?'
    ).exists()
    assert user_message, 'User message was not saved to the database'
 
    # Check assistant reply was saved
    assistant_message = ChatMessage.objects.filter(
        session=context.session,
        role='assistant',
        content='Here is a great recipe for chicken fried rice!'
    ).exists()
    assert assistant_message, 'Assistant reply was not saved to the database'