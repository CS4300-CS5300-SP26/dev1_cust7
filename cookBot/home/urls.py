from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    #Spoonacular API
    path('nutrition/<str:ingredient_name>/', views.get_nutrition, name='get_nutrition'),
    
    # Authentication & User Account Management
    path('register/', views.register, name='register'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='logout'),
    path('account/', views.account, name='account'),
    path('account/edit/', views.edit_account, name='edit_account'),
    path('account/change-password/', views.change_password, name='change_password'),
    
    # Pantry functionality
    path('pantry/', views.pantry_view, name='pantry'),
    path('pantry/add/', views.add_ingredient, name='add_ingredient'),
    path('pantry/delete/<int:ingredient_id>/', views.delete_ingredient, name='delete_ingredient'),
    path('pantry/api/', views.get_pantry_ingredients, name='get_pantry_ingredients'),
    path('pantry/search-recipes/', views.search_recipes_by_pantry, name='search_recipes_by_pantry'),
   
    # Meal Calendar API
    path('api/get-meals/', views.get_meals_json, name='get_meals'),
    path('api/generate-meal-plan/', views.generate_meal_plan, name='generate_meal_plan'),
    path('calendar/', views.calendar_view, name='calendar'),

    # Paths for create recipe and display recipe pages
    path('recipe/<int:recipe_id>/', views.recipe_view, name='recipe_view'),
    path('recipe/create/', views.create_recipe, name='create_recipe'),
    path('my-recipes/', views.my_recipes, name='my_recipes'),
    path("recipes/<int:recipe_id>/delete/", views.delete_recipe, name="delete_recipe"),

    #ChefBot openai
    path('aiChefBot/', views.aiChefBot_view, name='aiChefBot'),
    path('aiChefBot/chat/', views.aiChefBot_chat, name='aiChefBot_chat'),

    # Social feed
    path('social/', views.social_feed, name='social_feed'),

    # Kroger store finder
    path('kroger/stores/', views.find_kroger_stores, name='find_kroger_stores'),
]
