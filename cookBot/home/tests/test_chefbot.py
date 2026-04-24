import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase

from home.chefBot import collect_context_from_recipes, build_messages
from home.models import ChatSession, ChatMessage, Recipe


class TestContextFromRecipes(TestCase):

    def test_spoonacular_recipes_appear_in_context(self):
        """Spoonacular recipe titles and ingredients show up in the context block."""
        spoonacular = [
            {
                "title": "Chicken Fried Rice",
                "used_ingredients": ["chicken", "rice"],
                "missed_ingredients": [],
            }
        ]
        context = collect_context_from_recipes(spoonacular_recipes=spoonacular)
        self.assertIn("Chicken Fried Rice", context)
        self.assertIn("chicken", context)
        self.assertIn("rice", context)

    def test_saved_recipes_appear_in_context(self):
        """Saved recipe titles and ingredients show up in the context block."""
        saved = [
            {
                "title": "Pasta Carbonara",
                "ingredients": [
                    {"quantity": "200", "unit": "g", "name": "spaghetti"},
                    {"quantity": "2", "unit": "", "name": "eggs"},
                ],
            }
        ]
        context = collect_context_from_recipes(saved_recipes=saved)
        self.assertIn("Pasta Carbonara", context)
        self.assertIn("spaghetti", context)
        self.assertIn("eggs", context)

    def test_both_spoonacular_and_saved_recipes_appear_in_context(self):
        """Both Spoonacular and saved recipes appear together in the context block."""
        spoonacular = [
            {
                "title": "Chicken Soup",
                "used_ingredients": ["chicken"],
                "missed_ingredients": ["broth"],
            }
        ]
        saved = [
            {
                "title": "Beef Tacos",
                "ingredients": [{"quantity": "300", "unit": "g", "name": "beef"}],
            }
        ]
        context = collect_context_from_recipes(
            spoonacular_recipes=spoonacular, saved_recipes=saved
        )
        self.assertIn("Chicken Soup", context)
        self.assertIn("Beef Tacos", context)

    def test_empty_inputs_return_empty_string(self):
        """No recipes passed in returns an empty string."""
        context = collect_context_from_recipes()
        self.assertEqual(context, "")


class TestBuildMessages(TestCase):
    def test_system_prompt_is_first_message(self):
        """The first message is always the system prompt."""
        messages = build_messages([])
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("ChefBot", messages[0]["content"])

    def test_conversation_history_appended_after_system(self):
        """Conversation history is appended after the system prompt."""
        history = [
            {"role": "user", "content": "What can I cook?"},
            {"role": "assistant", "content": "Here is a recipe!"},
        ]
        messages = build_messages(history)
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[2]["role"], "assistant")

    def test_recipe_context_injected_into_system_prompt(self):
        """When recipes are passed, context is injected into the system prompt."""
        spoonacular = [
            {
                "title": "Chicken Fried Rice",
                "used_ingredients": ["chicken"],
                "missed_ingredients": [],
            }
        ]
        messages = build_messages([], spoonacular_recipes=spoonacular)
        system_content = messages[0]["content"]
        self.assertIn("USER RECIPE CONTEXT", system_content)
        self.assertIn("Chicken Fried Rice", system_content)

    def test_no_context_block_when_no_recipes(self):
        """When no recipes are passed, the context block is not added."""
        messages = build_messages([])
        system_content = messages[0]["content"]
        self.assertNotIn("USER RECIPE CONTEXT", system_content)

    def test_saved_recipes_injected_into_system_prompt(self):
        """Saved recipes are injected into the system prompt."""
        saved = [
            {
                "title": "Beef Tacos",
                "ingredients": [{"quantity": "300", "unit": "g", "name": "beef"}],
            }
        ]
        messages = build_messages([], saved_recipes=saved)
        system_content = messages[0]["content"]
        self.assertIn("Beef Tacos", system_content)


class TestChatSessionModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.session = ChatSession.objects.create(
            user=self.user,
            spoonacular_context=[],
        )

    def test_get_history_returns_messages_in_order(self):
        """get_history() returns messages ordered by timestamp."""
        ChatMessage.objects.create(session=self.session, role="user", content="Hello")
        ChatMessage.objects.create(
            session=self.session, role="assistant", content="Hi there!"
        )
        history = self.session.get_history()
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")

    def test_get_history_returns_correct_format_for_openai(self):
        """get_history() returns dicts with role and content keys only."""
        ChatMessage.objects.create(
            session=self.session, role="user", content="Test message"
        )
        history = self.session.get_history()
        self.assertIn("role", history[0])
        self.assertIn("content", history[0])
        self.assertNotIn("id", history[0])
        self.assertNotIn("timestamp", history[0])

    def test_get_history_empty_when_no_messages(self):
        """get_history() returns an empty list when no messages exist."""
        history = self.session.get_history()
        self.assertEqual(history, [])

    def test_spoonacular_context_stored_on_session(self):
        """Spoonacular recipe context is correctly stored on the session."""
        spoonacular = [
            {
                "title": "Chicken Soup",
                "used_ingredients": ["chicken"],
                "missed_ingredients": [],
            }
        ]
        session = ChatSession.objects.create(
            user=self.user,
            spoonacular_context=spoonacular,
        )
        self.assertEqual(session.spoonacular_context[0]["title"], "Chicken Soup")


class TestAiChefBotView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_unauthenticated_user_redirected(self):
        """Unauthenticated users are redirected away from the aiChefBot page."""
        unauthenticated_client = Client()
        response = unauthenticated_client.get("/aiChefBot/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/signin", response.url)

    @patch("home.spoonacular.spoonacular_get", return_value=[])
    def test_aichefbot_page_loads(self, mock_spoon):
        """aiChefBot page loads successfully for a logged in user."""
        response = self.client.get("/aiChefBot/")
        self.assertEqual(response.status_code, 200)

    @patch("home.spoonacular.spoonacular_get")
    def test_spoonacular_recipes_passed_to_template(self, mock_spoon):
        """Spoonacular recipes are fetched and passed to the template context."""
        mock_spoon.return_value = [
            {
                "title": "Chicken Fried Rice",
                "usedIngredients": [{"name": "chicken"}],
                "missedIngredients": [],
            }
        ]
        self.user.pantry_items.create(ingredient_name="chicken")
        response = self.client.get("/aiChefBot/")
        self.assertEqual(response.status_code, 200)
        spoon_recipes = response.context["spoonacular_recipes"]
        titles = [r["title"] for r in spoon_recipes]
        self.assertIn("Chicken Fried Rice", titles)

    @patch("home.spoonacular.spoonacular_get", return_value=[])
    def test_saved_recipes_passed_to_template(self, mock_spoon):
        """User's saved recipes are passed to the template context."""
        Recipe.objects.create(user=self.user, title="Pasta Carbonara", is_public=False)
        response = self.client.get("/aiChefBot/")
        self.assertEqual(response.status_code, 200)
        saved_recipes = response.context["saved_recipes"]
        titles = [r["title"] for r in saved_recipes]
        self.assertIn("Pasta Carbonara", titles)

    @patch("home.spoonacular.spoonacular_get", return_value=[])
    def test_chat_session_created_on_page_load(self, mock_spoon):
        """A new ChatSession is created each time the aiChefBot page loads."""
        self.client.get("/aiChefBot/")
        self.assertTrue(ChatSession.objects.filter(user=self.user).exists())


class TestAiChefBotChat(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")
        self.session = ChatSession.objects.create(
            user=self.user,
            spoonacular_context=[],
        )

    def post_chat(self, message, session_id=None):
        return self.client.post(
            "/aiChefBot/chat/",
            data=json.dumps(
                {
                    "session_id": session_id or self.session.id,
                    "message": message,
                }
            ),
            content_type="application/json",
        )

    @patch("home.views.call_openai", return_value="Here is a great recipe!")
    def test_successful_chat_returns_reply(self, mock_openai):
        """A valid message returns a reply from ChefBot."""
        response = self.post_chat("What can I cook with chicken?")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("reply", data)
        self.assertEqual(data["reply"], "Here is a great recipe!")

    @patch("home.views.call_openai", return_value="Here is a great recipe!")
    def test_user_message_saved_to_db(self, mock_openai):
        """User message is saved to the database after sending."""
        self.post_chat("What can I cook with chicken?")
        self.assertTrue(
            ChatMessage.objects.filter(
                session=self.session,
                role="user",
                content="What can I cook with chicken?",
            ).exists()
        )

    @patch("home.views.call_openai", return_value="Here is a great recipe!")
    def test_assistant_reply_saved_to_db(self, mock_openai):
        """ChefBot reply is saved to the database after responding."""
        self.post_chat("What can I cook with chicken?")
        self.assertTrue(
            ChatMessage.objects.filter(
                session=self.session,
                role="assistant",
                content="Here is a great recipe!",
            ).exists()
        )

    @patch("home.views.call_openai", return_value="Reply 3")
    def test_full_conversation_history_sent_to_openai(self, mock_openai):
        """The full conversation history is passed to call_openai on each message."""
        ChatMessage.objects.create(
            session=self.session, role="user", content="First message"
        )
        ChatMessage.objects.create(
            session=self.session, role="assistant", content="First reply"
        )
        self.post_chat("Second message")
        call_args = mock_openai.call_args
        history = (
            call_args[1]["conversation_history"] if call_args[1] else call_args[0][0]
        )
        self.assertEqual(len(history), 3)  # 2 existing + new user message

    @patch("home.views.call_openai", return_value="Recipe reply")
    def test_spoonacular_context_passed_to_openai(self, mock_openai):
        """Spoonacular context stored on the session is passed to call_openai."""
        self.session.spoonacular_context = [
            {
                "title": "Chicken Soup",
                "used_ingredients": ["chicken"],
                "missed_ingredients": [],
            }
        ]
        self.session.save()
        self.post_chat("What can I cook?")
        call_args = mock_openai.call_args
        spoon_arg = call_args[1].get("spoonacular_recipes") or call_args[0][1]
        self.assertEqual(spoon_arg[0]["title"], "Chicken Soup")

    @patch("home.views.call_openai", return_value="Recipe reply")
    def test_saved_recipes_passed_to_openai(self, mock_openai):
        """User's saved recipes are passed to call_openai."""
        Recipe.objects.create(user=self.user, title="Beef Tacos", is_public=False)
        self.post_chat("What can I cook?")
        call_args = mock_openai.call_args
        saved_arg = call_args[1].get("saved_recipes") or call_args[0][2]
        titles = [r["title"] for r in saved_arg]
        self.assertIn("Beef Tacos", titles)

    def test_empty_message_returns_400(self):
        """An empty message returns a 400 error."""
        response = self.post_chat("")
        self.assertEqual(response.status_code, 400)

    def test_invalid_session_id_returns_404(self):
        """An invalid session ID returns a 404 error."""
        response = self.post_chat("Hello", session_id=999999)
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_access_another_users_session(self):
        """A user cannot send messages to another user's chat session."""
        other_user = User.objects.create_user(
            username="otheruser", password="testpass123"
        )
        other_session = ChatSession.objects.create(
            user=other_user, spoonacular_context=[]
        )
        response = self.post_chat("Hello", session_id=other_session.id)
        self.assertEqual(response.status_code, 404)

    @patch("home.views.call_openai", side_effect=Exception("OpenAI is down"))
    def test_openai_failure_returns_500(self, mock_openai):
        """An OpenAI API failure returns a 500 error."""
        response = self.post_chat("What can I cook?")
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertIn("error", data)
