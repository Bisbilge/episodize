import traceback
from django.shortcuts import render
from django.http import JsonResponse
from .models import Movie
from .services import AIService, SubtitleService, MovieInfoService # Yeni servisi ekledik

def index(request):
    """Ana sayfayı gösterir."""
    return render(request, 'index.html')

def analyze_movie(request):
    try:
        # Artık buna sadece 'id' değil, genel olarak 'query' (sorgu) diyelim
        user_input = request.GET.get('imdb_id', '').strip()
        
        if not user_input:
            return JsonResponse({'error': 'Lütfen bir film adı veya IMDb ID girin.'}, status=400)

        info_service = MovieInfoService()
        imdb_id = None

        # --- KARAR MEKANİZMASI ---
        # Eğer girdi "tt" ile başlıyorsa ve rakam içeriyorsa bu bir ID'dir.
        if user_input.startswith('tt') and user_input[2:].isdigit():
            imdb_id = user_input
        else:
            # Değilse, bu bir film ismidir. ID'sini bulalım.
            print(f"🔎 İsimden aranıyor: {user_input}")
            found_id = info_service.search_id_by_title(user_input)
            if found_id:
                imdb_id = found_id
                print(f"✅ ID Bulundu: {imdb_id}")
            else:
                return JsonResponse({'error': f"'{user_input}' adında bir film bulunamadı."}, status=404)
        # -------------------------

        # BURADAN SONRASI AYNI (ID artık elimizde)
        
        # 1. Detayları Çek
        movie_info = info_service.get_movie_details(imdb_id)

        # 2. Veritabanı Kontrolü
        existing_movie = Movie.objects.filter(imdb_id=imdb_id).first()
        if existing_movie:
            return JsonResponse({
                'source': 'Veritabanı',
                'episodes': existing_movie.episode_data,
                'movie_info': movie_info
            })

        # Servisleri Başlat
        sub_service = SubtitleService()
        ai_service = AIService()

        # 3. Altyazı İndir
# 3. Altyazı İndir
        try:
            raw_sub = sub_service.get_subtitle(imdb_id)
        except Exception as e:
            # --- BU KISMI EKLEDİK ---
            print("-" * 30)
            print(f"❌ ALTYAZI İNDİRME HATASI OLUŞTU:")
            print(f"Hata Mesajı: {str(e)}")
            import traceback
            traceback.print_exc()
            print("-" * 30)
            # ------------------------
            return JsonResponse({'error': f"Altyazı Bulunamadı veya İndirilemedi: {str(e)}"}, status=404)

        # 4. AI Analizi
        clean_sub = ai_service.clean_subtitle(raw_sub)
        episodes = ai_service.split_movie_into_episodes(clean_sub)

        # Hata Kontrolü
        if isinstance(episodes, dict) and "error" in episodes:
             return JsonResponse({'error': f"AI Hatası: {episodes['error']}"}, status=500)

        # 5. Kaydet
        if isinstance(episodes, list) and len(episodes) > 0:
            Movie.objects.create(
                imdb_id=imdb_id,
                episode_data=episodes,
                title=movie_info['title'] if movie_info else f"Movie {imdb_id}"
            )
        else:
            return JsonResponse({'error': "AI anlamlı bir bölümleme yapamadı."}, status=500)

        return JsonResponse({
            'source': 'OpenSubtitles + Gemini AI',
            'episodes': episodes,
            'movie_info': movie_info
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'error': f"Sunucu Hatası: {str(e)}"}, status=500)
def autocomplete_movies(request):
    """Canlı arama için JSON döner."""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 3: # 3 harften azsa arama yapma (API tasarrufu)
        return JsonResponse({'results': []})

    info_service = MovieInfoService()
    results = info_service.search_candidates(query)
    
    return JsonResponse({'results': results})