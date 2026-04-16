import json
import urllib.error
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from home.models import Pantry
from .helpers import MOCK_NUTRITION_RESPONSE, MOCK_SEARCH_RESPONSE, make_mock_response


class NutritionViewTests(TestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )
        self.client = Client()
        self.client.login(username="testuser", password="password123")

    def test_pantry_view_status(self):
        """Tests that the pantry page loads for a logged-in user"""
        response = self.client.get(reverse("pantry"))
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("index"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_add_ingredient_success(self):
        """Tests adding an ingredient via AJAX"""
        data = {"ingredient_name": "Carrot"}
        response = self.client.post(
            reverse("add_ingredient"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Pantry.objects.filter(ingredient_name="Carrot").exists())

    def test_add_duplicate_ingredient(self):
        """Tests that duplicate ingredients are rejected (covers error lines)"""
        Pantry.objects.create(user=self.user, ingredient_name="Apple")
        data = {"ingredient_name": "Apple"}
        response = self.client.post(
            reverse("add_ingredient"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)  # Covers the 'exists()' check logic

    def test_delete_ingredient(self):
        """Tests removing an ingredient"""
        item = Pantry.objects.create(user=self.user, ingredient_name="Onion")
        response = self.client.post(reverse("delete_ingredient", args=[item.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Pantry.objects.filter(id=item.id).exists())

    def test_search_recipes_empty_pantry(self):
        """Tests recipe search logic when pantry is empty (covers early return lines)"""
        response = self.client.get(reverse("search_recipes_by_pantry"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("No ingredients in pantry", response.json().get("message", ""))

    @patch("home.spoonacular.urllib.request.urlopen")
    def test_search_recipes_with_ingredients_success(self, mock_urlopen):
        """Tests recipe search with ingredients (Mocking Spoonacular)"""
        Pantry.objects.create(user=self.user, ingredient_name="Chicken")
        mock_recipes = [
            {
                "id": 1,
                "title": "Chicken Soup",
                "image": "img.jpg",
                "usedIngredients": [{"name": "chicken"}],
                "missedIngredients": [],
            }
        ]
        mock_urlopen.return_value = make_mock_response(mock_recipes)
        response = self.client.get(reverse("search_recipes_by_pantry"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["recipes"]), 1)

    def test_get_fallback_recipes_logic(self):
        """Tests the fallback logic when no API is called"""
        from home.views import get_fallback_recipes

        pantry_items = ["Potato"]
        recipes = get_fallback_recipes(pantry_items)
        self.assertTrue(len(recipes) > 0)

    @patch("home.spoonacular.urllib.request.urlopen")
    def test_returns_nutrition_data_for_valid_ingredient(self, mock_urlopen):
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_SEARCH_RESPONSE),
            make_mock_response(MOCK_NUTRITION_RESPONSE),
        ]
        response = self.client.get(reverse("get_nutrition", args=["banana"]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["name"], "banana")
        self.assertIn("nutrition", data)

    @patch("home.spoonacular.urllib.request.urlopen")
    def test_returns_404_when_ingredient_not_found(self, mock_urlopen):
        mock_urlopen.return_value = make_mock_response(
            {"results": [], "totalResults": 0}
        )
        response = self.client.get(reverse("get_nutrition", args=["xyzunknown"]))
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn("error", data)

    @patch("home.spoonacular.urllib.request.urlopen")
    def test_returns_502_on_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        response = self.client.get(reverse("get_nutrition", args=["banana"]))
        self.assertEqual(response.status_code, 502)
        data = json.loads(response.content)
        self.assertIn("error", data)

    @patch("home.spoonacular.urllib.request.urlopen")
    def test_two_api_calls_are_made(self, mock_urlopen):
        cache.clear()
        mock_urlopen.side_effect = [
            make_mock_response(MOCK_SEARCH_RESPONSE),
            make_mock_response(MOCK_NUTRITION_RESPONSE),
        ]
        self.client.get(reverse("get_nutrition", args=["banana"]))
        self.assertEqual(mock_urlopen.call_count, 2)


class SpoonacularAndNutritionCoverageTests(TestCase):
    """
    Covers spoonacular.py and nutrition-related edge cases from MissingCoverageTests.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )

    @patch("home.spoonacular._get_next_key")
    def test_spoonacular_all_keys_exhausted(self, mock_get_key):
        """Test spoonacular.py line 23: All API keys exhausted scenario"""
        mock_get_key.return_value = None
        from home.spoonacular import spoonacular_get

        with self.assertRaises(Exception) as context:
            spoonacular_get("food/ingredients/search", {"query": "test"})
        self.assertIn("All Spoonacular API keys are exhausted", str(context.exception))

    @patch("home.spoonacular.cache.get")
    def test_spoonacular_cache_hit(self, mock_cache_get):
        """Test spoonacular.py line 31: Cache hit returns cached data without API call"""
        cached_data = {"results": [{"id": 1, "name": "cached"}]}
        mock_cache_get.return_value = cached_data
        from home.spoonacular import spoonacular_get

        with patch("home.spoonacular.urllib.request.urlopen") as mock_urlopen:
            result = spoonacular_get("food/ingredients/search", {"query": "test"})
            self.assertEqual(result, cached_data)
            mock_urlopen.assert_not_called()

    @patch("home.views.spoonacular_get")
    def test_get_nutrition_api_search_failure(self, mock_spoonacular):
        """Test views.py lines 41-45: API search failure in get_nutrition"""
        mock_spoonacular.side_effect = Exception("API timeout")
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("get_nutrition", args=["banana"]))
        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertIn("Search request failed", data["error"])

    @patch("home.views.spoonacular_get")
    def test_get_nutrition_no_ingredient_found(self, mock_spoonacular):
        """Test views.py line 51: No ingredient found in search results"""
        mock_spoonacular.return_value = {"results": []}
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("get_nutrition", args=["xyzunknown"]))
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("No ingredient found matching", data["error"])

    @patch("home.views.spoonacular_get")
    def test_get_nutrition_nutrition_api_failure(self, mock_spoonacular):
        """Test views.py lines 56-57: Nutrition API failure"""
        mock_spoonacular.side_effect = [
            {"results": [{"id": 1, "name": "banana"}]},
            Exception("Nutrition API down"),
        ]
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("get_nutrition", args=["banana"]))
        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertIn("Nutrition request failed", data["error"])

    def test_add_ingredient_json_parse_error(self):
        """Test views.py lines 120-165: JSON parsing error in add_ingredient"""
        self.client.login(username="testuser", password="password123")
        response = self.client.post(
            reverse("add_ingredient"),
            data="invalid json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)

    def test_add_ingredient_empty_name(self):
        """Test views.py lines 120-165: Empty ingredient name validation"""
        self.client.login(username="testuser", password="password123")
        response = self.client.post(
            reverse("add_ingredient"),
            data=json.dumps({"ingredient_name": ""}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Ingredient name is required")

    def test_add_ingredient_duplicate(self):
        """Test views.py lines 120-165: Duplicate ingredient prevention"""
        self.client.login(username="testuser", password="password123")
        response1 = self.client.post(
            reverse("add_ingredient"),
            data=json.dumps({"ingredient_name": "Apple"}),
            content_type="application/json",
        )
        self.assertEqual(response1.status_code, 200)
        response2 = self.client.post(
            reverse("add_ingredient"),
            data=json.dumps({"ingredient_name": "Apple"}),
            content_type="application/json",
        )
        self.assertEqual(response2.status_code, 400)
        data = response2.json()
        self.assertEqual(data["error"], "Ingredient already in pantry")

    def test_delete_ingredient_not_found(self):
        """Test views.py lines 120-165: Deleting non-existent ingredient"""
        self.client.login(username="testuser", password="password123")
        response = self.client.post(reverse("delete_ingredient", args=[999]))
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)

    @patch("home.spoonacular._get_next_key")
    def test_search_recipes_all_keys_exhausted(self, mock_get_key):
        """Test spoonacular.py line 23: All API keys exhausted raises exception in recipe search"""
        mock_get_key.return_value = None
        self.client.login(username="testuser", password="password123")
        Pantry.objects.create(user=self.user, ingredient_name="Chicken")
        response = self.client.get(reverse("search_recipes_by_pantry"))
        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertIn("error", data)

    def test_get_fallback_recipes_no_matches(self):
        """Test views.py lines 207-215: Fallback recipes when no ingredients match"""
        from home.views import get_fallback_recipes

        pantry_items = ["xyzunknown"]
        fallback = get_fallback_recipes(pantry_items)
        self.assertEqual(len(fallback), 1)
        self.assertEqual(fallback[0]["title"], "Basic Recipe Suggestions")
        self.assertEqual(fallback[0]["used_ingredient_count"], 0)

    def test_pantry_str_edge_case(self):
        """Test models.py line 17: Pantry.__str__ with edge case"""
        pantry = Pantry.objects.create(
            user=self.user, ingredient_name="Test Ingredient"
        )
        expected = f"{self.user.username} - Test Ingredient"
        self.assertEqual(str(pantry), expected)

    @patch("home.spoonacular.cache.get")
    def test_spoonacular_cache_miss(self, mock_cache_get):
        """Test spoonacular.py line 22: Cache miss scenario"""
        mock_cache_get.return_value = None
        from home.spoonacular import spoonacular_get

        with patch("home.spoonacular.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = make_mock_response(
                {"results": [{"id": 1, "name": "test"}]}
            )
            result = spoonacular_get("food/ingredients/search", {"query": "test"})
            self.assertEqual(result["results"][0]["name"], "test")
            mock_urlopen.assert_called_once()

    @patch("home.spoonacular.cache.set")
    def test_spoonacular_cache_timeout(self, mock_cache_set):
        """Test spoonacular.py lines 52-58: Cache timeout behavior"""
        from home.spoonacular import spoonacular_get

        cache.clear()
        with patch("home.spoonacular.cache.get", return_value=None):
            with patch("home.spoonacular.urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value = make_mock_response(
                    {"results": [{"id": 1, "name": "test"}]}
                )
                spoonacular_get("food/ingredients/search", {"query": "test"})
                self.assertTrue(mock_cache_set.called)
                call_kwargs = mock_cache_set.call_args.kwargs
                call_args = mock_cache_set.call_args[0]
                self.assertTrue(call_args[0].startswith("spoon_"))
                self.assertEqual(call_args[1]["results"][0]["name"], "test")
                self.assertEqual(call_kwargs.get("timeout"), 3600)

    @patch("home.views.spoonacular_get")
    def test_get_nutrition_invalid_json_response(self, mock_spoonacular):
        """Test views.py line 51: Invalid JSON response handling"""
        mock_spoonacular.return_value = {"invalid": "data"}
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("get_nutrition", args=["banana"]))
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("No ingredient found matching", data["error"])

    @patch("home.views.spoonacular_get")
    def test_get_nutrition_missing_fields(self, mock_spoonacular):
        """Test views.py lines 59-61, 66: Missing fields in API response - view returns raw data"""
        mock_spoonacular.side_effect = [
            {"results": [{"id": 1, "name": "banana"}]},
            {"id": 1, "name": "banana"},
        ]
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("get_nutrition", args=["banana"]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "banana")

    def test_add_ingredient_malformed_json(self):
        """Test views.py lines 140-141: Malformed JSON handling"""
        self.client.login(username="testuser", password="password123")
        response = self.client.post(
            reverse("add_ingredient"),
            data='{"ingredient_name": "Test',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)

    @patch("home.views.spoonacular_get")
    def test_search_recipes_rate_limiting(self, mock_spoonacular):
        """Test views.py lines 194-204: API rate limiting (HTTP 429)"""
        mock_spoonacular.side_effect = urllib.error.HTTPError(
            url="test", code=429, msg="Too Many Requests", hdrs={}, fp=None
        )
        self.client.login(username="testuser", password="password123")
        Pantry.objects.create(user=self.user, ingredient_name="Chicken")
        response = self.client.get(reverse("search_recipes_by_pantry"))
        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertIn("error", data)

    def test_get_fallback_recipes_edge_cases(self):
        """Test views.py lines 257-262: Fallback recipes edge cases"""
        from home.views import get_fallback_recipes

        fallback = get_fallback_recipes([])
        self.assertEqual(len(fallback), 1)
        self.assertEqual(fallback[0]["title"], "Basic Recipe Suggestions")
        fallback = get_fallback_recipes(["café", "piñata"])
        self.assertTrue(len(fallback) > 0)
        long_name = "a" * 100
        fallback = get_fallback_recipes([long_name])
        self.assertTrue(len(fallback) > 0)

    def test_delete_ingredient_exception_handling(self):
        """Test views.py lines 151-152: Exception handling in delete_ingredient"""
        self.client.login(username="testuser", password="password123")
        response = self.client.post(reverse("delete_ingredient", args=[99999]))
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)

    @patch("home.views.spoonacular_get")
    def test_search_recipes_payment_required(self, mock_spoonacular):
        """Test search_recipes_by_pantry handles HTTP 402 Payment Required"""
        self.client.login(username="testuser", password="password123")
        Pantry.objects.create(user=self.user, ingredient_name="Chicken")
        mock_spoonacular.side_effect = urllib.error.HTTPError(
            url="test", code=402, msg="Payment Required", hdrs={}, fp=None
        )
        response = self.client.get(reverse("search_recipes_by_pantry"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("api_status", data)
        self.assertEqual(data["api_status"], "payment_required")

    def test_nutrition_test_view(self):
        """Test nutrition_test view function exists and is callable"""
        from home.views import nutrition_test

        self.assertIsNotNone(nutrition_test)

    def test_get_pantry_ingredients(self):
        """Test get_pantry_ingredients returns JSON"""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("get_pantry_ingredients"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ingredients", data)

    def test_get_pantry_ingredients_requires_login(self):
        """Test that get_pantry_ingredients redirects when not logged in"""
        response = self.client.get(reverse("get_pantry_ingredients"))
        self.assertIn(response.status_code, [302, 403])
