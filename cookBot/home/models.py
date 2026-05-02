from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_delete
from django.dispatch import receiver
from PIL import Image
from PIL import UnidentifiedImageError
import os


class Pantry(models.Model):
    """Model to store user's pantry ingredients"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="pantry_items"
    )
    ingredient_name = models.CharField(max_length=100)
    added_date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [
            "user",
            "ingredient_name",
        ]  # Prevent duplicate ingredients per user
        ordering = ["ingredient_name"]  # Sort ingredients alphabetically

    def __str__(self):
        return f"{self.user.username} - {self.ingredient_name}"


class Tag(models.Model):
    """A Tag system for recipes"""

    class TagType(models.TextChoices):
        """A sub model for tags to help filter and define them"""

        DIETARY = "dietary", "Dietary"  # vegan, gluten-free, nut-free
        CUISINE = "cuisine", "Cuisine"  # french, italian, thai, bbq
        COOK_TIME = "cooktime", "Cook Time"  # 15-20 mins, under 30 mins
        MEAL_TYPE = "meal", "Meal Type"  # breakfast, dinner, snack
        OTHER = "other", "Other"  # spicy, one-pan, meal-prep

    name = models.CharField(max_length=150, unique=True)
    tag_type = models.CharField(
        max_length=30, choices=TagType.choices, default=TagType.OTHER
    )
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["tag_type", "name"]

    def __str__(self):
        return f"[{self.tag_type}] {self.name}"


class Recipe(models.Model):
    def recipe_image_path(instance, filename):
        ext = filename.split(".")[-1]
        return f"recipes/images/{instance.id}.{ext}"

    """Model to store recipes with ingredients and instructions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recipes")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)  # False = private, True = public
    created_date = models.DateTimeField(default=timezone.now)
    tags = models.ManyToManyField(
        Tag, through="RecipeTag", related_name="recipes", blank=True
    )
    favorites = models.ManyToManyField(
        User, related_name="favorite_recipes", blank=True
    )
    image = models.ImageField(upload_to=recipe_image_path, blank=True, null=True)

    class Meta:
        ordering = ["title"]  # Sort recipes alphabetically

    def average_rating(self):
        """Returns the average star rating from all user ratings, or None if no ratings exist"""
        ratings = self.ratings.all()
        if not ratings:
            return None
        return sum(r.stars for r in ratings) / len(ratings)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image and os.path.exists(self.image.path):
            try:
                img = Image.open(self.image.path)
                # Fix RGBA / P mode for JPEGs
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail((800, 800))
                img.save(self.image.path)
            except UnidentifiedImageError:
                pass
            except Exception:
                pass


class RecipeStep(models.Model):
    """Model to store individual ordered steps for a recipe"""

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="steps")
    order = models.IntegerField()
    text = models.TextField()

    class Meta:
        ordering = ["order"]  # Always return steps in order

    def __str__(self):
        return f"{self.recipe.title} - Step {self.order}"


class RecipeIngredient(models.Model):
    """Model to store individual ingredients for a recipe"""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="ingredients"
    )
    name = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50)
    unit = models.CharField(max_length=50, blank=True, null=True)  # Unit is optional

    class Meta:
        ordering = ["name"]  # Sort ingredients alphabetically

    def __str__(self):
        return f"{self.recipe.title} - {self.name}"


class RecipeRating(models.Model):
    """Model to store individual user ratings for a recipe"""

    STAR_CHOICES = [
        (1, "1 Star"),
        (2, "2 Stars"),
        (3, "3 Stars"),
        (4, "4 Stars"),
        (5, "5 Stars"),
    ]

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recipe_ratings"
    )
    stars = models.IntegerField(choices=STAR_CHOICES)
    rated_date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ["recipe", "user"]  # One rating per user per recipe
        ordering = ["rated_date"]

    def __str__(self):
        return f"{self.user.username} - {self.recipe.title} - {self.stars} stars"


class RecipeTag(models.Model):
    """Model linking recipes to tags"""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="recipe_tags"
    )
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="recipe_tags")
    tagged_date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ["recipe", "tag"]

    def __str__(self):
        return f"{self.recipe.title} — {self.tag.name}"


class MealPlan(models.Model):
    """Model to store user's meal calendar entries"""

    MEAL_TYPE_CHOICES = [
        ("Breakfast", "Breakfast"),
        ("Lunch", "Lunch"),
        ("Dinner", "Dinner"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="meal_plans")
    recipe_name = models.CharField(max_length=200)
    recipe_id = models.IntegerField(blank=True, null=True)
    # Optional, for linking to external APIs
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)
    calories = models.IntegerField(blank=True, null=True)
    protein = models.IntegerField(blank=True, null=True)
    fat = models.IntegerField(blank=True, null=True)
    carbs = models.IntegerField(blank=True, null=True)
    recipes = models.ManyToManyField(Recipe, related_name="meal_plans", blank=True)
    recipe_data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ["user", "date", "meal_type"]  # One meal per slot per user
        ordering = ["date", "meal_type"]

    def __str__(self):
        return f"{self.user.username} - {self.meal_type} on {self.date}: {self.recipe_name}"


# conversation history between the user and ChefBot
# Stores spoonacular recipe information for consistent recipe information
class ChatSession(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_sessions"
    )
    created_date = models.DateTimeField(default=timezone.now)
    pantry_context = models.JSONField(default=list, blank=True)

    # Spoonacular results
    spoonacular_context = models.JSONField(default=list, blank=True)

    class Meta:
        # Most recent session
        ordering = ["-created_date"]

    def __str__(self):
        return f"{self.user.username} - Session {self.id} ({self.created_date.strftime('%Y-%m-%d')})"

    # Conversation history as a list of role/content dicts fro OpenAI
    def get_history(self):
        return list(self.messages.order_by("timestamp").values("role", "content"))


# Save chat messages to the DB from both the user and ChefBot(assistant)
class ChatMessage(models.Model):
    ROLES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=ROLES)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.role}] Session {self.session.id} @ {self.timestamp.strftime('%H:%M:%S')}"


# Method to delete recipe images when a recipe is deleted
@receiver(post_delete, sender=Recipe)
def delete_recipe_image(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


class Comment(models.Model):
    """User comments on recipes"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="comments"
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
        db_column="parent_id",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} on {self.recipe.title}"


class UserStreak(models.Model):
    """Tracks a user's cooking streak"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="streak")
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_cooked_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} — Current: {self.current_streak}, Longest: {self.longest_streak}"
