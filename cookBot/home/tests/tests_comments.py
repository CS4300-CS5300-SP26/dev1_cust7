from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from home.models import Recipe, Comment


class CommentTests(TestCase):
    def setUp(self):
        """Set up test user and test recipe before each test"""
        self.user = User.objects.create_user(
            username="test_user", password="testpass123"
        )
        self.recipe = Recipe.objects.create(
            user=self.user, title="Test Recipe for Comments", is_public=True
        )
        self.post_comment_url = reverse("post_comment", args=[self.recipe.id])

    def test_authentication_required_to_post_comment(self):
        """Test that unauthenticated users cannot post comments"""
        response = self.client.post(
            self.post_comment_url, {"text": "This is a test comment"}
        )
        # Should redirect to login or return 403
        self.assertIn(response.status_code, [302, 403])
        # Verify no comment was created
        self.assertEqual(Comment.objects.count(), 0)

    def test_logged_in_user_can_post_comment(self):
        """Test that authenticated user can successfully post a comment"""
        self.client.login(username="test_user", password="testpass123")

        comment_text = "This recipe was amazing! I made it for dinner."
        response = self.client.post(self.post_comment_url, {"text": comment_text})

        # Check response is success
        self.assertEqual(response.status_code, 302)

        # Verify comment was saved to database
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.text, comment_text)
        self.assertEqual(comment.user, self.user)

    def test_comment_correctly_associated_with_recipe(self):
        """Test that comments are properly linked to the correct recipe"""
        # Create second recipe for comparison
        other_recipe = Recipe.objects.create(
            user=self.user, title="Other Recipe", is_public=True
        )

        self.client.login(username="test_user", password="testpass123")
        comment_text = "Great recipe!"

        # Post comment to first recipe
        self.client.post(self.post_comment_url, {"text": comment_text})

        # Verify comment is on the correct recipe
        self.assertEqual(self.recipe.comments.count(), 1)
        self.assertEqual(other_recipe.comments.count(), 0)

        comment = self.recipe.comments.first()
        self.assertEqual(comment.recipe, self.recipe)

    def test_comment_has_created_timestamp(self):
        """Test that comments automatically get created_at timestamp"""
        self.client.login(username="test_user", password="testpass123")

        self.client.post(self.post_comment_url, {"text": "Testing timestamp"})

        comment = Comment.objects.first()
        self.assertIsNotNone(comment.created_at)

    def test_empty_comment_not_allowed(self):
        """Test that empty comments cannot be submitted"""
        self.client.login(username="test_user", password="testpass123")

        self.client.post(self.post_comment_url, {"text": ""})

        # Verify no comment was created
        self.assertEqual(Comment.objects.count(), 0)

    def test_can_post_reply_to_comment(self):
        """Test that replies can be posted to existing comments"""
        self.client.login(username="test_user", password="testpass123")

        # Create parent comment first
        parent_comment = Comment.objects.create(
            user=self.user, recipe=self.recipe, text="This is the parent comment"
        )

        # Post reply
        reply_text = "This is a reply to the parent comment"
        response = self.client.post(
            self.post_comment_url,
            {
                "text": reply_text,
                "parent_id": str(
                    parent_comment.id
                ),  # Explicitly send as string like browser does
            },
        )

        # Verify redirect
        self.assertEqual(response.status_code, 302)

        # Get the newly created comment FRESH from database
        fresh_reply = Comment.objects.latest("id")

        # Verify reply is linked correctly
        self.assertEqual(fresh_reply.parent_id, parent_comment.id)
        self.assertEqual(fresh_reply.recipe, self.recipe)
        self.assertEqual(fresh_reply.text, reply_text)

        # Refresh parent object from database to see new reply
        parent_comment.refresh_from_db()

        # Verify parent has the reply
        self.assertEqual(parent_comment.replies.count(), 1)
        self.assertEqual(parent_comment.replies.first(), fresh_reply)

    def test_cannot_reply_to_comment_from_other_recipe(self):
        """Test that replies cannot be attached to comments from different recipes"""
        self.client.login(username="test_user", password="testpass123")

        # Create second recipe and comment
        other_recipe = Recipe.objects.create(
            user=self.user, title="Other Recipe", is_public=True
        )
        other_comment = Comment.objects.create(
            user=self.user, recipe=other_recipe, text="Comment from another recipe"
        )

        # Attempt to reply to other recipe's comment on this recipe
        response = self.client.post(
            self.post_comment_url,
            {"text": "Malicious cross recipe reply", "parent_id": other_comment.id},
        )

        # Should return 404 Not Found for invalid parent comment
        self.assertEqual(response.status_code, 404)

        # Comment should NOT be created at all (transaction aborted due to exception)
        self.assertEqual(Comment.objects.count(), 1)

    def test_cannot_comment_on_private_recipe(self):
        """Test that only the owner can comment on private recipes"""
        # Create private recipe
        private_recipe = Recipe.objects.create(
            user=self.user, title="Private Recipe", is_public=False
        )
        private_url = reverse("post_comment", args=[private_recipe.id])

        # Create another user
        User.objects.create_user(username="other_user", password="testpass123")
        self.client.login(username="other_user", password="testpass123")

        # Attempt to comment on private recipe
        response = self.client.post(
            private_url, {"text": "Trying to comment on private recipe"}
        )

        # Should get 403 Forbidden
        self.assertEqual(response.status_code, 403)

        # No comment created
        self.assertEqual(Comment.objects.count(), 0)
