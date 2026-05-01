from behave import given, when, then
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import Client
from home.models import ChatSession, ChatMessage, Recipe, RecipeIngredient, RecipeStep
from home.chefBot import (
    collect_context_from_recipes,
    build_messages,
    call_openai,
)
import json
import urllib.error

# Mock parsed recipe returned by parse_recipe_from_text
MOCK_PARSED_RECIPE = {
    "title": "Chicken Fried Rice",
    "ingredients": [
        {"quantity": "2", "unit": "cups", "name": "rice"},
        {"quantity": "1", "unit": "", "name": "egg"},
        {"quantity": "200", "unit": "g", "name": "chicken"},
    ],
    "steps": [
        "Cook the rice according to package instructions.",
        "Fry the chicken in a pan until golden.",
        "Mix everything together and serve hot.",
    ],
}

MOCK_NOT_A_RECIPE = {"error": "not_a_recipe"}


# GIVEN
@given("I am not logged in")
def step_not_logged_in(context):

    context.client = Client()


@given("I am a logged in user with a chat session")
def step_logged_in_with_session(context):
    context.client = Client()

    User.objects.filter(username="testuser").delete()
    user = User.objects.create_user(username="testuser", password="testpass123")

    context.client.post(
        "/signin/",
        {
            "username": "testuser",
            "password": "testpass123",
        },
    )

    # Create a chat session for this user
    context.session = ChatSession.objects.create(
        user=user,
        spoonacular_context=[],
    )
    context.user = user


@given("I am a logged in user with saved recipes")
def step_logged_in_with_saved_recipes(context):

    context.client = Client()

    User.objects.filter(username="testuser").delete()
    user = User.objects.create_user(username="testuser", password="testpass123")

    context.client.post(
        "/signin/",
        {
            "username": "testuser",
            "password": "testpass123",
        },
    )

    # Create two saved recipes for this user
    Recipe.objects.create(user=user, title="Chicken Stir Fry", is_public=False)
    Recipe.objects.create(user=user, title="Pasta Carbonara", is_public=False)


@given("I am a logged in user with pantry ingredients")
def step_logged_in_with_pantry(context):

    context.client = Client()

    User.objects.filter(username="testuser").delete()
    user = User.objects.create_user(username="testuser", password="testpass123")

    context.client.post(
        "/signin/",
        {
            "username": "testuser",
            "password": "testpass123",
        },
    )

    # Add pantry ingredients for this user
    user.pantry_items.create(ingredient_name="chicken")
    user.pantry_items.create(ingredient_name="rice")


@given("I am a logged in user with a chat session with Spoonacular context")
def step_logged_in_with_spoonacular_context(context):

    context.client = Client()

    User.objects.filter(username="testuser").delete()
    user = User.objects.create_user(username="testuser", password="testpass123")

    context.client.post(
        "/signin/",
        {
            "username": "testuser",
            "password": "testpass123",
        },
    )

    context.session = ChatSession.objects.create(
        user=user,
        spoonacular_context=[
            {
                "title": "Chicken Fried Rice",
                "used_ingredients": ["chicken", "rice"],
                "missed_ingredients": [],
            }
        ],
    )


@given("I am a logged in user with a chat session and saved recipes")
def step_logged_in_with_session_and_saved_recipes(context):

    context.client = Client()

    User.objects.filter(username="testuser").delete()
    user = User.objects.create_user(username="testuser", password="testpass123")

    context.client.post(
        "/signin/",
        {
            "username": "testuser",
            "password": "testpass123",
        },
    )

    Recipe.objects.create(user=user, title="Beef Tacos", is_public=False)

    context.session = ChatSession.objects.create(
        user=user,
        spoonacular_context=[],
    )


@given("I am a logged in user with a chat session and a recipe response")
def step_logged_in_with_recipe_response(context):
    context.client = Client()
    User.objects.filter(username="testuser").delete()
    user = User.objects.create_user(username="testuser", password="testpass123")
    context.client.post("/signin/", {"username": "testuser", "password": "testpass123"})
    context.session = ChatSession.objects.create(user=user, spoonacular_context=[])
    context.user = user
    # Save a realistic recipe response as the last assistant message
    ChatMessage.objects.create(
        session=context.session,
        role="assistant",
        content=(
            "Here is a great Chicken Fried Rice recipe!\n"
            "Ingredients: 2 cups rice, 1 egg, 200g chicken\n"
            "Steps: 1. Cook rice. 2. Fry chicken. 3. Mix together."
        ),
    )


@given("I am a logged in user with a chat session and a tip response")
def step_logged_in_with_tip_response(context):
    context.client = Client()
    User.objects.filter(username="testuser").delete()
    user = User.objects.create_user(username="testuser", password="testpass123")
    context.client.post("/signin/", {"username": "testuser", "password": "testpass123"})
    context.session = ChatSession.objects.create(user=user, spoonacular_context=[])
    context.user = user
    # Save a cooking tip (not a recipe) as the last assistant message
    ChatMessage.objects.create(
        session=context.session,
        role="assistant",
        content="A great tip for cooking pasta is to salt your water generously before boiling.",
    )


@given("I have Spoonacular recipes")
def step_have_spoonacular_recipes(context):
    context.spoonacular_recipes = [
        {
            "title": "Chicken Fried Rice",
            "used_ingredients": ["chicken", "rice"],
            "missed_ingredients": [],
        },
        {
            "title": "Chicken Soup",
            "used_ingredients": ["chicken"],
            "missed_ingredients": ["broth"],
        },
    ]


@given("I have saved recipe data")
def step_have_saved_recipes(context):
    context.saved_recipes = [
        {
            "title": "Beef Tacos",
            "ingredients": [{"quantity": "300", "unit": "g", "name": "beef"}],
        }
    ]


@given("I have no recipe data")
def step_have_no_recipe_data(context):
    context.spoonacular_recipes = None
    context.saved_recipes = None


@given("I have a conversation history")
def step_have_conversation_history(context):
    context.conversation_history = [
        {"role": "user", "content": "What can I cook?"},
        {"role": "assistant", "content": "Here is a recipe!"},
    ]


# WHEN
@when("I visit the aiChefBot page")
def step_visit_aichefbot(context):
    context.response = context.client.get("/aiChefBot/")


@when("I visit the aiChefBot page with mocked Spoonacular")
def step_visit_aichefbot_mocked_spoonacular(context):
    # Mock Spoonacular so we don't make real API calls
    mock_spoonacular_results = [
        {
            "title": "Chicken Fried Rice",
            "usedIngredients": [{"name": "chicken"}, {"name": "rice"}],
            "missedIngredients": [],
        },
        {
            "title": "Chicken Soup",
            "usedIngredients": [{"name": "chicken"}],
            "missedIngredients": [{"name": "broth"}],
        },
    ]
    context.client.session
    user = User.objects.get(username="testuser")
    user.pantry_items.get_or_create(ingredient_name="chicken")

    with patch(
        "home.spoonacular.spoonacular_get", return_value=mock_spoonacular_results
    ):
        context.response = context.client.get("/aiChefBot/")


@when("I submit an empty message to the chat")
def step_submit_empty_message(context):
    context.response = context.client.post(
        "/aiChefBot/chat/",
        data=json.dumps({"session_id": context.session.id, "message": ""}),
        content_type="application/json",
    )


@when("I submit a message with an invalid session ID")
def step_submit_invalid_session(context):
    context.response = context.client.post(
        "/aiChefBot/chat/",
        data=json.dumps({"session_id": 999999, "message": "Hello ChefBot"}),
        content_type="application/json",
    )


@when("the OpenAI API fails")
def step_openai_fails(context):
    context.openai_patch = patch(
        "home.views.call_openai", side_effect=Exception("OpenAI is down")
    )
    context.openai_patch.start()


@when("I send a message")
def step_send_message(context):
    context.response = context.client.post(
        "/aiChefBot/chat/",
        data=json.dumps(
            {"session_id": context.session.id, "message": "What can I cook?"}
        ),
        content_type="application/json",
    )
    # Stop the patch after the request is made
    context.openai_patch.stop()


@when("I send a valid message to ChefBot")
def step_send_valid_message(context):
    # Capture the actual args passed to call_openai so we can assert on them
    with patch(
        "home.views.call_openai", return_value="Here is a great recipe!"
    ) as mock:
        context.openai_mock = mock
        context.response = context.client.post(
            "/aiChefBot/chat/",
            data=json.dumps(
                {"session_id": context.session.id, "message": "What can I cook?"}
            ),
            content_type="application/json",
        )
        context.openai_call_args = mock.call_args


@when("I click save recipe")
def step_click_save_recipe(context):
    with patch("home.views.parse_recipe_from_text", return_value=MOCK_PARSED_RECIPE):
        context.response = context.client.post(
            "/aiChefBot/save-recipe/",
            data=json.dumps({"session_id": context.session.id}),
            content_type="application/json",
        )


@when("I click save recipe with mocked not a recipe response")
def step_click_save_recipe_not_a_recipe(context):
    with patch("home.views.parse_recipe_from_text", return_value=MOCK_NOT_A_RECIPE):
        context.response = context.client.post(
            "/aiChefBot/save-recipe/",
            data=json.dumps({"session_id": context.session.id}),
            content_type="application/json",
        )


@when("I try to save a recipe without logging in")
def step_save_recipe_not_logged_in(context):
    context.response = context.client.post(
        "/aiChefBot/save-recipe/",
        data=json.dumps({"session_id": 1}),
        content_type="application/json",
    )


@when("I try to save a recipe from another users session")
def step_save_recipe_another_users_session(context):
    other_user = User.objects.create_user(username="otheruser", password="testpass123")
    other_session = ChatSession.objects.create(user=other_user, spoonacular_context=[])
    ChatMessage.objects.create(
        session=other_session, role="assistant", content="Some recipe content"
    )
    context.response = context.client.post(
        "/aiChefBot/save-recipe/",
        data=json.dumps({"session_id": other_session.id}),
        content_type="application/json",
    )


@when("I try to save a recipe with an invalid session ID")
def step_save_recipe_invalid_session(context):
    context.response = context.client.post(
        "/aiChefBot/save-recipe/",
        data=json.dumps({"session_id": 999999}),
        content_type="application/json",
    )


@when("I collect context from those recipes")
def step_collect_context(context):
    context.result = collect_context_from_recipes(
        spoonacular_recipes=getattr(context, "spoonacular_recipes", None),
        saved_recipes=getattr(context, "saved_recipes", None),
    )


@when("I build messages for OpenAI")
def step_build_messages(context):
    context.messages = build_messages(context.conversation_history)


@when("I build messages with that recipe context")
def step_build_messages_with_context(context):
    context.messages = build_messages(
        [],
        spoonacular_recipes=context.spoonacular_recipes,
    )


@when("the OpenAI API returns an error")
def step_openai_returns_error(context):
    import io

    mock_fp = io.BytesIO(b'{"error": "invalid key"}')
    mock_error = urllib.error.HTTPError(
        url="https://api.openai.com",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=mock_fp,
    )
    with patch("urllib.request.urlopen", side_effect=mock_error):
        try:
            call_openai(context.conversation_history)
            context.exception = None
        except Exception as e:
            context.exception = str(e)


# THEN
@then("I should be redirected to the sign in page")
def step_redirected_to_signin(context):
    assert context.response.status_code == 302
    assert "/signin" in context.response.url


@then("I should receive a 404 error response")
def step_receive_404(context):
    assert context.response.status_code == 404
    data = json.loads(context.response.content)
    assert "error" in data


@then("I should receive a 500 error response")
def step_receive_500(context):
    assert context.response.status_code == 500
    data = json.loads(context.response.content)
    assert "error" in data


@then("I should see my saved recipes on the page")
def step_see_saved_recipes(context):
    assert context.response.status_code == 200
    content = context.response.content.decode("utf-8")
    assert "Chicken Stir Fry" in content
    assert "Pasta Carbonara" in content


@then("I should see the Spoonacular suggested recipes on the page")
def step_see_spoonacular_recipes(context):
    assert context.response.status_code == 200
    content = context.response.content.decode("utf-8")
    assert "Chicken Fried Rice" in content
    assert "Chicken Soup" in content


@then("I should receive a reply from ChefBot")
def step_receive_reply(context):
    assert context.response.status_code == 200
    data = json.loads(context.response.content)
    assert "reply" in data
    assert len(data["reply"]) > 0


@then("the message and reply should be saved to the database")
def step_messages_saved_to_db(context):

    # Check user message was saved
    user_message = ChatMessage.objects.filter(
        session=context.session, role="user", content="What can I cook?"
    ).exists()
    assert user_message, "User message was not saved to the database"

    # Check assistant reply was saved
    assistant_message = ChatMessage.objects.filter(
        session=context.session, role="assistant", content="Here is a great recipe!"
    ).exists()
    assert assistant_message, "Assistant reply was not saved to the database"


@then("the OpenAI call should include Spoonacular recipe context")
def step_openai_has_spoonacular_context(context):
    call_kwargs = context.openai_call_args[1]
    spoon_recipes = call_kwargs.get("spoonacular_recipes", [])
    titles = [r["title"] for r in spoon_recipes]
    assert "Chicken Fried Rice" in titles, f"Expected Chicken Fried Rice in {titles}"


@then("the OpenAI call should include saved recipe context")
def step_openai_has_saved_recipe_context(context):
    call_kwargs = context.openai_call_args[1]
    saved_recipes = call_kwargs.get("saved_recipes", [])
    titles = [r["title"] for r in saved_recipes]
    assert "Beef Tacos" in titles, f"Expected Beef Tacos in {titles}"


@then("the OpenAI call should have the system prompt as the first message")
def step_openai_has_system_prompt_first(context):
    call_kwargs = context.openai_call_args[1]
    history = call_kwargs.get("conversation_history", [])
    # The system prompt is added inside build_messages, not in history
    # So we verify the history starts with the user message
    messages = build_messages(history)
    assert (
        messages[0]["role"] == "system"
    ), f"Expected system role first, got {messages[0]['role']}"
    assert "ChefBot" in messages[0]["content"], "System prompt does not contain ChefBot"


@then("the context should contain the Spoonacular recipe titles")
def step_context_has_spoonacular_titles(context):
    assert "Chicken Fried Rice" in context.result
    assert "Chicken Soup" in context.result


@then("the context should contain the saved recipe titles")
def step_context_has_saved_titles(context):
    assert "Beef Tacos" in context.result


@then("the context should be empty")
def step_context_is_empty(context):
    assert context.result == ""


@then("the first message should be the system prompt")
def step_first_message_is_system(context):
    assert context.messages[0]["role"] == "system"
    assert "ChefBot" in context.messages[0]["content"]


@then("the system prompt should contain the recipe context")
def step_system_prompt_has_context(context):
    system_content = context.messages[0]["content"]
    assert "USER RECIPE CONTEXT" in system_content
    assert "Chicken Fried Rice" in system_content


@then("an exception should be raised with the error details")
def step_exception_raised(context):
    assert context.exception is not None
    assert "OpenAI API error" in context.exception


@then("the recipe should be saved to my recipes")
def step_recipe_saved(context):
    assert context.response.status_code == 200
    data = json.loads(context.response.content)
    assert data.get("success") is True
    assert Recipe.objects.filter(
        user=context.user, title="Chicken Fried Rice"
    ).exists(), "Recipe was not saved to the database"


@then("I should receive a success response with the recipe title")
def step_success_response_with_title(context):
    data = json.loads(context.response.content)
    assert "recipe_title" in data
    assert data["recipe_title"] == "Chicken Fried Rice"


@then("I should receive a 400 error saying no response found")
def step_400_no_response_found(context):
    assert context.response.status_code == 400
    data = json.loads(context.response.content)
    assert "error" in data
    assert (
        "no chefbot response" in data["error"].lower() or "no" in data["error"].lower()
    )


@then("I should receive a 400 error saying not a recipe")
def step_400_not_a_recipe(context):
    assert context.response.status_code == 400
    data = json.loads(context.response.content)
    assert "error" in data
    assert "recipe" in data["error"].lower()


@then("the saved recipe should be private")
def step_saved_recipe_is_private(context):
    recipe = Recipe.objects.filter(
        user=context.user, title="Chicken Fried Rice"
    ).first()
    assert recipe is not None, "Recipe was not found in the database"
    assert recipe.is_public is False, "Recipe should be private by default"


@then("the saved recipe should have ingredients and steps")
def step_saved_recipe_has_ingredients_and_steps(context):
    recipe = Recipe.objects.filter(
        user=context.user, title="Chicken Fried Rice"
    ).first()
    assert recipe is not None, "Recipe was not found in the database"
    assert RecipeIngredient.objects.filter(
        recipe=recipe
    ).exists(), "Recipe has no ingredients"
    assert RecipeStep.objects.filter(recipe=recipe).exists(), "Recipe has no steps"
