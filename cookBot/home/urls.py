from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    #Spoonacular API
    path('nutrition/<str:ingredient_name>/', views.get_nutrition, name='get_nutrition'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='logout'),
    
    # Pantry functionality
    path('pantry/', views.pantry_view, name='pantry'),
    path('pantry/add/', views.add_ingredient, name='add_ingredient'),
    path('pantry/delete/<int:ingredient_id>/', views.delete_ingredient, name='delete_ingredient'),
    path('pantry/api/', views.get_pantry_ingredients, name='get_pantry_ingredients'),
    path('pantry/search-recipes/', views.search_recipes_by_pantry, name='search_recipes_by_pantry'),
]
