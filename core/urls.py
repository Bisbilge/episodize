from django.contrib import admin # Bu satırın olduğundan emin ol
from django.urls import path
from movie_app import views

urlpatterns = [
    # ADMIN EN ÜSTTE OLMALI
    path('admin/', admin.site.urls), 

    # Diğer sabit yollar
    path('', views.index, name='index'),
    path('analyze/', views.analyze_movie, name='analyze'),
    path('autocomplete/', views.autocomplete_movies, name='autocomplete'),
    path('open/<str:imdb_id>/', views.open_movie_by_id, name='open_movie'),

    # SLUG EN ALTTA OLMALI
    path('<slug:slug>/', views.movie_detail, name='movie_detail'),
]