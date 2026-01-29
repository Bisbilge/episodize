from django.db import models

class Movie(models.Model):
    # Film adı
    title = models.CharField(max_length=255, blank=True, null=True)
    # IMDb ID (Benzersiz anahtarımız)
    imdb_id = models.CharField(max_length=50, unique=True)
    # AI'dan gelen bölüm verileri (JSON formatında saklanır)
    episode_data = models.JSONField()
    # Kayıt tarihi
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.imdb_id