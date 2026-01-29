from django.db import models
from django.utils.text import slugify
import unidecode # Eğer yüklü değilse: pip install unidecode

class Movie(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    imdb_id = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True) # YENİ ALAN
    episode_data = models.JSONField(default=list, blank=True) # Boş olabilir
    movie_info = models.JSONField(default=dict, blank=True) # Cache için
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Eğer slug yoksa ve başlık varsa oluştur
        if not self.slug and self.title:
            # Türkçe karakterleri İngilizce karşılıklarına çevir (Ş -> s, ı -> i)
            base_slug = slugify(unidecode.unidecode(self.title))
            self.slug = base_slug
            
            # Eğer bu slug zaten varsa sonuna ID ekle (Matrix ve Matrix Reloaded karışmasın)
            if Movie.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{base_slug}-{self.imdb_id}"
        
        super(Movie, self).save(*args, **kwargs)

    def __str__(self):
        return self.title or self.imdb_id