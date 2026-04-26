from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.index, name="index"),
    # Spoonacular API
    path("nutrition/<str:ingredient_name>/", views.get_nutrition, name="get_nutrition"),
    # Authentication & User Account Management
    path("register/", views.register, name="register"),
    path("signin/", views.signin, name="signin"),
    path("logout/", views.signout, name="logout"),
    path("account/", views.account, name="account"),
    path("account/edit/", views.edit_account, name="edit_account"),
    path("account/change-password/", views.change_password, name="change_password"),
    # Pantry functionality
    path("pantry/", views.pantry_view, name="pantry"),
    path("pantry/add/", views.add_ingredient, name="add_ingredient"),
    path(
        "pantry/delete/<int:ingredient_id>/",
        views.delete_ingredient,
        name="delete_ingredient",
    ),
    path("pantry/api/", views.get_pantry_ingredients, name="get_pantry_ingredients"),
    path(
        "pantry/search-recipes/",
        views.search_recipes_by_pantry,
        name="search_recipes_by_pantry",
    ),
    # Meal Calendar API
    path("api/get-meals/", views.get_meals_json, name="get_meals"),
    path(
        "api/generate-meal-plan/", views.generate_meal_plan, name="generate_meal_plan"
    ),
    path("calendar/", views.calendar_view, name="calendar"),
    path("meal-plan-history/", views.meal_plan_history, name="meal_plan_history"),
    path(
        "meal-plan/<int:meal_plan_id>/",
        views.meal_plan_detail,
        name="meal_plan_detail",
    ),
    # Streak endpoints
    path("api/increment-streak/", views.increment_streak, name="increment_streak"),
    path("api/reset-streak/", views.reset_streak, name="reset_streak"),
    # Paths for create/edit recipe, search for recipes, and display recipe pages
    path("recipe/<int:recipe_id>/", views.recipe_view, name="recipe_view"),
    path("recipe/create/", views.create_recipe, name="create_recipe"),
    path("recipe/<int:recipe_id>/edit/", views.edit_recipe, name="edit_recipe"),
    path("my-recipes/", views.my_recipes, name="my_recipes"),
    path("recipes/<int:recipe_id>/delete/", views.delete_recipe, name="delete_recipe"),
    path("search/", views.search_recipes, name="search_recipes"),
    # ChefBot openai
    path("aiChefBot/", views.aiChefBot_view, name="aiChefBot"),
    path("aiChefBot/chat/", views.aiChefBot_chat, name="aiChefBot_chat"),
    # Social feed
    path("social/", views.social_feed, name="social_feed"),
    # Kroger store finder
    path("kroger/stores/", views.find_kroger_stores, name="find_kroger_stores"),
    # Comments
    path("recipe/<int:recipe_id>/comment/", views.post_comment, name="post_comment"),
    # Favorites functionality
    path(
        "toggle-favorite/<int:recipe_id>/",
        views.toggle_favorite,
        name="toggle_favorite",
    ),
    path("favorites/", views.favorites_list, name="favorites_list"),
    # Ratings functionality
    path("recipe/<int:recipe_id>/rate/", views.rate_recipe, name="rate_recipe"),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
