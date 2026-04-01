from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Pantry(models.Model):
    """Model to store user's pantry ingredients"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pantry_items')
    ingredient_name = models.CharField(max_length=100)
    added_date = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['user', 'ingredient_name']  # Prevent duplicate ingredients per user
        ordering = ['ingredient_name']  # Sort ingredients alphabetically
    
    def __str__(self):
        return f"{self.user.username} - {self.ingredient_name}"

class Recipe(models.Model):
    """Model to store recipes with ingredients and instructions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipes')
    title = models.CharField(max_length=200)
    is_public = models.BooleanField(default=False)  # False = private, True = public
    created_date = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['title']  # Sort recipes alphabetically
 
    def average_rating(self):
        """Returns the average star rating from all user ratings, or None if no ratings exist"""
        ratings = self.ratings.all()
        if not ratings:
            return None
        return sum(r.stars for r in ratings) / len(ratings)
 
    def __str__(self):
        return f"{self.user.username} - {self.title}"

class RecipeStep(models.Model):
    """Model to store individual ordered steps for a recipe"""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='steps')
    order = models.IntegerField()
    text = models.TextField()
 
    class Meta:
        ordering = ['order']  # Always return steps in order
 
    def __str__(self):
        return f"{self.recipe.title} - Step {self.order}"
        
class RecipeIngredient(models.Model):
    """Model to store individual ingredients for a recipe"""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    name = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50)
    unit = models.CharField(max_length=50, blank=True, null=True)  # Unit is optional
 
    class Meta:
        ordering = ['name']  # Sort ingredients alphabetically
 
    def __str__(self):
        return f"{self.recipe.title} - {self.name}"

class RecipeRating(models.Model):
    """Model to store individual user ratings for a recipe"""
 
    STAR_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
 
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipe_ratings')
    stars = models.IntegerField(choices=STAR_CHOICES)
    rated_date = models.DateTimeField(default=timezone.now)
 
    class Meta:
        unique_together = ['recipe', 'user']  # One rating per user per recipe
        ordering = ['rated_date']
 
    def __str__(self):
        return f"{self.user.username} - {self.recipe.title} - {self.stars} stars"
