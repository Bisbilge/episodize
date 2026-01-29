from django.contrib import admin
from django.urls import path
from movie_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),        # Ana sayfa
    path('analyze/', views.analyze_movie, name='analyze'), # API ucu
    # urls.py içindeki urlpatterns listesine ekle:
    path('autocomplete/', views.autocomplete_movies, name='autocomplete'),
]