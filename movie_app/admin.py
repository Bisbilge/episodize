from django.contrib import admin
from .models import Movie

# Bu dekoratör, Movie modelini admin panelinde şık gösterir
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'imdb_id', 'created_at') # Listede görünecek sütunlar
    search_fields = ('title', 'imdb_id')             # Arama çubuğu ekler
    list_filter = ('created_at',)                    # Tarihe göre filtreleme ekler