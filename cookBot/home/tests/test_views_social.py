from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from home.models import Recipe, RecipeRating


class SocialFeedTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')
        self.client.login(username='testuser', password='password123')

    def test_social_feed_loads_for_logged_in_user(self):
        """Given a user is logged in, the social feed page loads successfully"""
        response = self.client.get(reverse('social_feed'))
        self.assertEqual(response.status_code, 200)

    def test_social_feed_redirects_logged_out_user(self):
        """Given a user is not logged in, they are redirected away from the feed"""
        self.client.logout()
        response = self.client.get(reverse('social_feed'))
        self.assertEqual(response.status_code, 302)

    def test_social_feed_shows_public_recipes(self):
        """Given a public recipe exists, it appears in the social feed"""
        Recipe.objects.create(user=self.other_user, title='Public Pasta', is_public=True)
        response = self.client.get(reverse('social_feed'))
        self.assertIn('Public Pasta', response.content.decode())

    def test_social_feed_does_not_show_private_recipes(self):
        """Given a private recipe exists, it does not appear in the social feed"""
        Recipe.objects.create(user=self.other_user, title='Secret Soup', is_public=False)
        response = self.client.get(reverse('social_feed'))
        self.assertNotIn('Secret Soup', response.content.decode())

    def test_social_feed_shows_recipes_from_all_users(self):
        """Given public recipes from multiple users exist, all appear in the feed"""
        Recipe.objects.create(user=self.user, title='My Public Recipe', is_public=True)
        Recipe.objects.create(user=self.other_user, title='Their Public Recipe', is_public=True)
        response = self.client.get(reverse('social_feed'))
        content = response.content.decode()
        self.assertIn('My Public Recipe', content)
        self.assertIn('Their Public Recipe', content)

    def test_social_feed_is_ordered_newest_first(self):
        """Given multiple public recipes exist, they are returned newest first"""
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()
        older_recipe = Recipe.objects.create(user=self.user, title='Older Recipe', is_public=True)
        Recipe.objects.filter(id=older_recipe.id).update(created_date=now - timedelta(days=1))
        newer_recipe = Recipe.objects.create(user=self.other_user, title='Newer Recipe', is_public=True)
        Recipe.objects.filter(id=newer_recipe.id).update(created_date=now)

        response = self.client.get(reverse('social_feed'))
        recipes = list(response.context['public_recipes'])
        self.assertGreaterEqual(len(recipes), 2)
        for i in range(len(recipes) - 1):
            self.assertGreaterEqual(recipes[i].created_date, recipes[i + 1].created_date)

    def test_social_feed_empty_when_no_public_recipes(self):
        """Given no public recipes exist, the feed context contains an empty list"""
        response = self.client.get(reverse('social_feed'))
        self.assertEqual(len(response.context['public_recipes']), 0)

    def test_public_recipe_links_to_recipe_page(self):
        """Given a public recipe is in the feed, it links to the correct recipe page"""
        recipe = Recipe.objects.create(user=self.other_user, title='Linkable Recipe', is_public=True)
        response = self.client.get(reverse('social_feed'))
        expected_url = reverse('recipe_view', args=[recipe.id])
        self.assertIn(expected_url, response.content.decode())

    def test_making_recipe_public_adds_it_to_feed(self):
        """Given a private recipe is updated to public, it appears in the feed"""
        recipe = Recipe.objects.create(user=self.user, title='Soon Public', is_public=False)
        response = self.client.get(reverse('social_feed'))
        self.assertNotIn('Soon Public', response.content.decode())
        recipe.is_public = True
        recipe.save()
        response = self.client.get(reverse('social_feed'))
        self.assertIn('Soon Public', response.content.decode())

    def test_making_recipe_private_removes_it_from_feed(self):
        """Given a public recipe is updated to private, it no longer appears in the feed"""
        recipe = Recipe.objects.create(user=self.user, title='Going Private', is_public=True)
        response = self.client.get(reverse('social_feed'))
        self.assertIn('Going Private', response.content.decode())
        recipe.is_public = False
        recipe.save()
        response = self.client.get(reverse('social_feed'))
        self.assertNotIn('Going Private', response.content.decode())

    def test_social_feed_shows_recipe_author(self):
        """Given a public recipe is in the feed, the author's username is displayed"""
        Recipe.objects.create(user=self.other_user, title='Authored Recipe', is_public=True)
        response = self.client.get(reverse('social_feed'))
        self.assertIn('otheruser', response.content.decode())

    def test_social_feed_shows_star_rating(self):
        """Given a public recipe has ratings, the average star rating is displayed"""
        recipe = Recipe.objects.create(user=self.other_user, title='Rated Recipe', is_public=True)
        RecipeRating.objects.create(recipe=recipe, user=self.user, stars=4)
        response = self.client.get(reverse('social_feed'))
        self.assertIn('4.0', response.content.decode())

    def test_social_feed_links_to_recipe_page(self):
        """Given a public recipe is in the feed, it links to the correct recipe page"""
        recipe = Recipe.objects.create(user=self.other_user, title='Linkable Recipe', is_public=True)
        response = self.client.get(reverse('social_feed'))
        expected_url = reverse('recipe_view', args=[recipe.id])
        self.assertIn(expected_url, response.content.decode())

    def test_social_feed_only_shows_public_recipes_in_context(self):
        """Given a mix of public and private recipes exist, context only contains public ones"""
        Recipe.objects.create(user=self.user, title='Public One', is_public=True)
        Recipe.objects.create(user=self.user, title='Private One', is_public=False)
        response = self.client.get(reverse('social_feed'))
        titles = [r.title for r in response.context['public_recipes']]
        self.assertIn('Public One', titles)
        self.assertNotIn('Private One', titles)