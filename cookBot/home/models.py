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
    instructions = models.TextField()
    created_date = models.DateTimeField(default=timezone.now)
 
    class Meta:
        ordering = ['title']  # Sort recipes alphabetically
 
    def __str__(self):
        return f"{self.user.username} - {self.title}"
 