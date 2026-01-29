import os
import re
import json
import requests
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
        if not raw_text: return ""
        clean_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', raw_text)
        clean_text = re.sub(r'<[^>]*>', '', clean_text)
        return " ".join(clean_text.split())

    def split_movie_into_episodes(self, subtitle_text):
            prompt = f"""
            You are an expert film editor and screenwriter. Your task is to transform a full-length movie into a "mini-series" format by splitting these subtitles into logical, narrative-driven episodes.

            CRITICAL GUIDELINES:
            1. **Narrative Arc**: Do not just look at the clock. Each episode must feel like a complete chapter. Find natural breaking points such as:
            - Major scene transitions or changes in location.
            - Emotional shifts or the conclusion of a sub-plot.
            - "Cliffhanger" moments that would make a viewer want to watch the next part.
            
            2. **Duration**: Aim for approximately 20-35 minutes per episode, but PRIORITIZE the story flow over exact timing. If a natural break happens at 18 minutes or 38 minutes, use that instead of forcing a break at 30.

            3. **Full Coverage**: You MUST process the subtitles from the very first second (00:00:00) to the final timestamp (the end of the credits). 

            4. **Titles**: Create a creative, thematic title for each episode based on the events occurring in that segment.

            RETURN ONLY A RAW JSON ARRAY. No markdown, no "json" blocks, no conversational text.
            
            Format:
            [
                {{"episode": 1, "start": "00:00:00", "end": "HH:MM:SS", "title": "The Beginning of the End"}},
                ...
                {{"episode": N, "start": "HH:MM:SS", "end": "FINAL_TIMESTAMP", "title": "Final Resolution"}}
            ]

            Subtitles:
            {subtitle_text} 
            """
            
            try:
                # Buradaki model ayarlarında temperature'ı biraz düşürmek (örn: 0.3) 
                # JSON formatının bozulmamasını sağlar.
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt
                )
                text_response = response.text
                
                # Markdown temizleme
                clean_json = text_response.replace('```json', '').replace('```', '').strip()
                return json.loads(clean_json)
            except Exception as e:
                print(f"AI Error: {e}")
                return [{"episode": 1, "title": f"Hata: {str(e)}", "start": "00:00:00", "end": "???"}]

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

    def search_id_by_title(self, title):
        candidates = self.search_candidates(title)
        return candidates[0]['imdbID'] if candidates else None

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
                    'genre': data.get('Genre')
                }
            return None
        except Exception:
            return None

class SubtitleService:
    def __init__(self):
        self.api_key = os.getenv("OPENSUBTITLES_API_KEY")
        self.base_url = "https://api.opensubtitles.com/api/v1"
        
        # User-Agent'ı gerçek bir tarayıcı gibi gösteriyoruz
        self.headers = {
            'Api-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json', 
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_subtitle(self, imdb_id):
        clean_id = int(imdb_id.replace('tt', ''))
        print(f"🌍 OpenSubtitles: {clean_id} aranıyor...")
        
        # 1. ARAMA
        search_url = f"{self.base_url}/subtitles?imdb_id={clean_id}&languages=tr,en&order_by=download_count&sort=desc"
        response = requests.get(search_url, headers=self.headers)
        response.raise_for_status()
        data = response.json()

        if not data['data']:
            raise Exception("Altyazı bulunamadı.")

        first_match = data['data'][0]
        file_id = first_match['attributes']['files'][0]['file_id']
        file_name = first_match['attributes']['files'][0]['file_name']
        print(f"✅ Dosya Seçildi: {file_name} (ID: {file_id})")

        # 2. İNDİRME LİNKİ
        dl_payload = {"file_id": file_id}
        
        dl_response = requests.post(
            f"{self.base_url}/download", 
            json=dl_payload, 
            headers=self.headers
        )
        
        # HATA VARSA İÇERİĞİNİ GÖRELİM (DEBUG)
        if dl_response.status_code != 200:
            print(f"⚠️ API HATASI DÖNDÜ: {dl_response.status_code}")
            print(f"⚠️ İÇERİK: {dl_response.text}")
            dl_response.raise_for_status()
        
        link_data = dl_response.json()
        download_link = link_data.get('link')

        # 3. İNDİR
        # Dosyayı indirirken header kullanmıyoruz (S3 linki çünkü)
        file_content = requests.get(download_link).text
        return file_content