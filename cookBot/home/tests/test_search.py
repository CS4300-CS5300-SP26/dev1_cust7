from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from home.models import Recipe, Tag


class SearchPageTests(TestCase):

    def setUp(self):
        self.user, _ = User.objects.get_or_create(username="testchef")
        self.user.set_password("pass")
        self.user.save()

        self.other_user, _ = User.objects.get_or_create(username="otherchef")
        self.other_user.set_password("pass")
        self.other_user.save()

        self.vegan_tag, _ = Tag.objects.get_or_create(
            name="Vegan", defaults={"tag_type": "dietary"}
        )
        self.italian_tag, _ = Tag.objects.get_or_create(
            name="Italian", defaults={"tag_type": "cuisine"}
        )
        self.breakfast_tag, _ = Tag.objects.get_or_create(
            name="Breakfast", defaults={"tag_type": "meal"}
        )

        self.public_recipe = Recipe.objects.create(
            user=self.user, title="Vegan Pasta", is_public=True
        )
        self.public_recipe.tags.add(self.vegan_tag, self.italian_tag)

        self.other_public_recipe = Recipe.objects.create(
            user=self.other_user, title="Scrambled Eggs", is_public=True
        )
        self.other_public_recipe.tags.add(self.breakfast_tag)

        self.private_recipe = Recipe.objects.create(
            user=self.user, title="Secret Soup", is_public=False
        )

    # ── Page load ──

    def test_search_page_loads(self):
        response = self.client.get(reverse("search_recipes"))
        self.assertEqual(response.status_code, 200)

    def test_search_page_loads_for_unauthenticated_user(self):
        response = self.client.get(reverse("search_recipes"))
        self.assertEqual(response.status_code, 200)

    def test_search_page_shows_all_public_recipes_by_default(self):
        response = self.client.get(reverse("search_recipes"))
        self.assertContains(response, "Vegan Pasta")
        self.assertContains(response, "Scrambled Eggs")

    def test_private_recipes_never_appear_in_search(self):
        response = self.client.get(reverse("search_recipes"))
        self.assertNotContains(response, "Secret Soup")

    def test_private_recipes_not_shown_even_when_logged_in_as_owner(self):
        self.client.login(username="testchef", password="pass")
        response = self.client.get(reverse("search_recipes"))
        self.assertNotContains(response, "Secret Soup")

    # ── Text search ──

    def test_search_by_recipe_title(self):
        response = self.client.get(reverse("search_recipes"), {"q": "pasta"})
        self.assertContains(response, "Vegan Pasta")
        self.assertNotContains(response, "Scrambled Eggs")

    def test_search_by_title_is_case_insensitive(self):
        response = self.client.get(reverse("search_recipes"), {"q": "PASTA"})
        self.assertContains(response, "Vegan Pasta")

    def test_search_by_username(self):
        response = self.client.get(reverse("search_recipes"), {"q": "otherchef"})
        self.assertContains(response, "Scrambled Eggs")
        self.assertNotContains(response, "Vegan Pasta")

    def test_search_by_partial_username(self):
        response = self.client.get(reverse("search_recipes"), {"q": "other"})
        self.assertContains(response, "Scrambled Eggs")

    def test_search_with_no_matches_shows_no_results(self):
        response = self.client.get(reverse("search_recipes"), {"q": "xyznotarecipe"})
        self.assertContains(response, "No recipes found")

    def test_empty_search_returns_all_public_recipes(self):
        response = self.client.get(reverse("search_recipes"), {"q": ""})
        self.assertContains(response, "Vegan Pasta")
        self.assertContains(response, "Scrambled Eggs")

    # ── Tag filtering ──

    def test_filter_by_single_tag(self):
        response = self.client.get(
            reverse("search_recipes"), {"tags": self.vegan_tag.id}
        )
        self.assertContains(response, "Vegan Pasta")
        self.assertNotContains(response, "Scrambled Eggs")

    def test_filter_by_multiple_tags_returns_recipes_with_all_tags(self):
        response = self.client.get(
            reverse("search_recipes"),
            {"tags": [self.vegan_tag.id, self.italian_tag.id]},
        )
        self.assertContains(response, "Vegan Pasta")
        self.assertNotContains(response, "Scrambled Eggs")

    def test_filter_by_tags_with_no_matches(self):
        response = self.client.get(
            reverse("search_recipes"),
            {"tags": [self.vegan_tag.id, self.breakfast_tag.id]},
        )
        self.assertContains(response, "No recipes found")

    def test_tag_options_are_shown_on_search_page(self):
        response = self.client.get(reverse("search_recipes"))
        self.assertContains(response, "Vegan")
        self.assertContains(response, "Italian")
        self.assertContains(response, "Breakfast")

    # ── Combined search and filter ──

    def test_search_query_combined_with_tag_filter(self):
        response = self.client.get(
            reverse("search_recipes"), {"q": "pasta", "tags": self.vegan_tag.id}
        )
        self.assertContains(response, "Vegan Pasta")
        self.assertNotContains(response, "Scrambled Eggs")

    def test_search_query_with_tag_filter_no_match(self):
        response = self.client.get(
            reverse("search_recipes"), {"q": "eggs", "tags": self.vegan_tag.id}
        )
        self.assertContains(response, "No recipes found")

    # ── Context ──

    def test_result_count_is_correct(self):
        response = self.client.get(reverse("search_recipes"), {"q": "pasta"})
        self.assertEqual(response.context["result_count"], 1)

    def test_query_is_preserved_in_context(self):
        response = self.client.get(reverse("search_recipes"), {"q": "pasta"})
        self.assertEqual(response.context["query"], "pasta")

    def test_selected_tag_ids_are_preserved_in_context(self):
        response = self.client.get(
            reverse("search_recipes"), {"tags": self.vegan_tag.id}
        )
        self.assertIn(self.vegan_tag.id, response.context["selected_tag_ids"])


class IndexPageTagTests(TestCase):

    def setUp(self):
        self.vegan_tag, _ = Tag.objects.get_or_create(
            name="Vegan", defaults={"tag_type": "dietary"}
        )
        self.italian_tag, _ = Tag.objects.get_or_create(
            name="Italian", defaults={"tag_type": "cuisine"}
        )

    def test_index_page_shows_tags_for_browsing(self):
        response = self.client.get(reverse("index"))
        self.assertContains(response, "Vegan")
        self.assertContains(response, "Italian")

    def test_index_page_tag_links_point_to_search(self):
        response = self.client.get(reverse("index"))
        self.assertContains(response, "/search/")
