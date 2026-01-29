from django.core.management.base import BaseCommand
from movie_app.services import AIService
import os

class Command(BaseCommand):
    help = 'Tests the movie splitting logic using a local test.srt file'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting test...'))
        
        file_path = 'test.srt'
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'{file_path} not found!'))
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        ai_service = AIService()
        
        # Önce temizle (Token tasarrufu)
        self.stdout.write('Cleaning subtitles...')
        clean_content = ai_service.clean_subtitle(raw_content)
        
        # Gemini'ye gönder
        self.stdout.write('Sending to Gemini (this may take a few seconds)...')
        result = ai_service.split_movie_into_episodes(clean_content)
        
        self.stdout.write(self.style.SUCCESS('--- Result from AI ---'))
        self.stdout.write(result)