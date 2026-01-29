from django.contrib import admin
from .models import Movie

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    # Listede görünecek sütunlar
    list_display = ('title', 'imdb_id', 'slug', 'created_at')
    
    # Arama yapılacak alanlar
    search_fields = ('title', 'imdb_id', 'slug')
    
    # Filtreleme
    list_filter = ('created_at',)
    
    # Otomatik slug oluşturma (Panelde elle yazarken kolaylık sağlar)
    prepopulated_fields = {'slug': ('title',)}