from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    #Spoonacular API
    path('nutrition/<str:ingredient_name>/', views.get_nutrition, name='get_nutrition'),
]
