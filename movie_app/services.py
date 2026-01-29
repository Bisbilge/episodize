import os
import re
import json
import requests
import io
import traceback
import subliminal
from babelfish import Language
from google import genai
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(
            api_key=api_key,
            http_options={'api_version': 'v1alpha'} 
        )
        self.model_id = "models/gemini-2.5-flash"

    def clean_subtitle(self, raw_text):
        """Altyazıdaki zaman kodlarını ve teknik verileri temizler."""
        if not raw_text: 
            return ""
        
        # 1. Zaman kodlarını ve satır numaralarını temizle (00:00:00,000 --> ...)
        clean_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', raw_text)
        
        # 2. HTML etiketlerini temizle (<i>, <b> vb.)
        clean_text = re.sub(r'<[^>]*>', '', clean_text)
        
        # 3. Reklam içerikli satırları temizle (Örn: OpenSubtitles, Translated by)
        clean_text = re.sub(r'(?i)(opensubtitles|subtitles|translated|encoded|advertisement).*', '', clean_text)
        
        # 4. Gereksiz boşlukları ve yeni satırları temizle
        return " ".join(clean_text.split())

    def split_movie_into_episodes(self, subtitle_text):
        """Filmi bölümlere ayırmak için AI kullanır. Bu fonksiyon AIService içindedir."""
        prompt = f"""
        You are a senior film producer. I am giving you the COMPLETE script (subtitles) of a movie. 
        Your task is to deconstruct this movie into a detailed 4 to 8 episode mini-series.

        STRICT REQUIREMENTS:
        1. **Don't Rush**: Analyze every part of the text. Do not skip the middle or the end.
        2. **Episode Length**: Each episode MUST be between 20 and 40 minutes of movie time. 
        3. **Total Coverage**: The last episode MUST end exactly at the final timestamp of the provided subtitles. 
        4. **Deep Analysis**: Identify major plot points, character introductions, and climaxes to determine where an episode ends.
        5. **Titles**: Give each episode a title that captures its core dramatic question.

        RETURN ONLY A RAW JSON ARRAY. No conversational filler.
        Format:
        [
            {{"episode": 1, "start": "00:00:00", "end": "00:32:15", "title": "The Silent Arrival"}},
            ...
        ]

        Subtitles to process:
        {subtitle_text} 
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            text_response = response.text
            # Markdown bloklarını temizle
            clean_json = text_response.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            print(f"AI Error: {e}")
            return [{"episode": 1, "title": f"Analiz Hatası: {str(e)}", "start": "00:00:00", "end": "???"}]

class MovieInfoService:
    def __init__(self):
        self.api_key = os.getenv("OMDB_API_KEY")
        self.base_url = "http://www.omdbapi.com/"

    def search_candidates(self, query):
        if not self.api_key: return []
        try:
            params = {'apikey': self.api_key, 's': query, 'type': 'movie'}
            response = requests.get(self.base_url, params=params)
            data = response.json()
            if data.get('Response') == 'True' and data.get('Search'):
                return data['Search'][:5]
            return []
        except Exception:
            return []

    def get_movie_details(self, imdb_id):
        if not self.api_key: return None
        try:
            params = {'apikey': self.api_key, 'i': imdb_id, 'plot': 'full'}
            response = requests.get(self.base_url, params=params)
            data = response.json()
            if data.get('Response') == 'True':
                return {
                    'title': data.get('Title'),
                    'year': data.get('Year'),
                    'poster': data.get('Poster'),
                    'plot': data.get('Plot'),
                    'imdb_rating': data.get('imdbRating'),
                    'genre': data.get('Genre'),
                    'runtime': data.get('Runtime')
                }
            return None
        except Exception:
            return None

class SubtitleService:
    def __init__(self):
        self.api_key = os.getenv("OPENSUBTITLES_API_KEY")
        self.base_url = "https://api.opensubtitles.com/api/v1"
        self.headers = {
            'Api-Key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }

    def get_subtitle(self, imdb_id):
        """OpenSubtitles API üzerinden altyazı indirir."""
        try:
            clean_id = int(imdb_id.replace('tt', ''))
            print(f"🌍 OpenSubtitles: {clean_id} aranıyor...")
            
            search_url = f"{self.base_url}/subtitles?imdb_id={clean_id}&languages=tr,en"
            response = requests.get(search_url, headers=self.headers)
            data = response.json()

            if not data.get('data'):
                return None

            file_id = data['data'][0]['attributes']['files'][0]['file_id']
            dl_response = requests.post(f"{self.base_url}/download", json={"file_id": file_id}, headers=self.headers)
            download_link = dl_response.json().get('link')

            if download_link:
                return requests.get(download_link).text
            return None
        except Exception as e:
            print(f"OpenSubtitles Error: {e}")
            return None

    def get_subtitle_alt(self, movie_title):
        """Subliminal kullanarak alternatif kaynaklardan indirir."""
        try:
            print(f"📡 Subliminal ile aranıyor: {movie_title}")
            video = subliminal.Video.fromname(movie_title)
            languages = {Language('eng'), Language('tur')}
            best_subs = subliminal.download_best_subtitles([video], languages)
            
            if video in best_subs and best_subs[video]:
                sub = best_subs[video][0]
                return sub.content.decode('utf-8', errors='ignore')
            return None
        except Exception as e:
            print(f"Subliminal Error: {e}")
            return None