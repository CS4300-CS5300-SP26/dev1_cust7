from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from home.models import Recipe, Comment


class CommentTests(TestCase):
    def setUp(self):
        """Set up test user and test recipe before each test"""
        self.user = User.objects.create_user(username='test_user', password='testpass123')
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe for Comments',
            is_public=True
        )
        self.post_comment_url = reverse('post_comment', args=[self.recipe.id])

    def test_authentication_required_to_post_comment(self):
        """Test that unauthenticated users cannot post comments"""
        response = self.client.post(self.post_comment_url, {
            'text': 'This is a test comment'
        })
        # Should redirect to login or return 403
        self.assertIn(response.status_code, [302, 403])
        # Verify no comment was created
        self.assertEqual(Comment.objects.count(), 0)

    def test_logged_in_user_can_post_comment(self):
        """Test that authenticated user can successfully post a comment"""
        self.client.login(username='test_user', password='testpass123')
        
        comment_text = "This recipe was amazing! I made it for dinner."
        response = self.client.post(self.post_comment_url, {
            'text': comment_text
        })
        
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
            user=self.user,
            title='Other Recipe',
            is_public=True
        )
        
        self.client.login(username='test_user', password='testpass123')
        comment_text = "Great recipe!"
        
        # Post comment to first recipe
        self.client.post(self.post_comment_url, {'text': comment_text})
        
        # Verify comment is on the correct recipe
        self.assertEqual(self.recipe.comments.count(), 1)
        self.assertEqual(other_recipe.comments.count(), 0)
        
        comment = self.recipe.comments.first()
        self.assertEqual(comment.recipe, self.recipe)

    def test_comment_has_created_timestamp(self):
        """Test that comments automatically get created_at timestamp"""
        self.client.login(username='test_user', password='testpass123')
        
        self.client.post(self.post_comment_url, {'text': 'Testing timestamp'})
        
        comment = Comment.objects.first()
        self.assertIsNotNone(comment.created_at)

    def test_empty_comment_not_allowed(self):
        """Test that empty comments cannot be submitted"""
        self.client.login(username='test_user', password='testpass123')
        
        response = self.client.post(self.post_comment_url, {'text': ''})
        
        # Verify no comment was created
        self.assertEqual(Comment.objects.count(), 0)