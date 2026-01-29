import traceback
import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Movie
from .services import AIService, SubtitleService, MovieInfoService

# --- MOD AYARI ---
# True: API'leri atlar, sadece ana dizindeki 'test.srt' dosyasını okur.
# False: Gerçek dünya modu. Önce OpenSubtitles, sonra Subliminal dener.
TEST_MODE = False 

def index(request):
    """Ana Sayfa: Veritabanındaki filmleri listeler."""
    movies = Movie.objects.exclude(title__isnull=True).order_by('-created_at')
    return render(request, 'index.html', {'movies': movies})

def open_movie_by_id(request, imdb_id):
    """
    ID -> Slug Köprüsü:
    Kullanıcı arama kutusundan bir filme tıkladığında buraya gelir.
    Sistem isme göre SEO uyumlu URL (slug) oluşturur ve oraya yönlendirir.
    """
    imdb_id = imdb_id.strip()
    
    movie = Movie.objects.filter(imdb_id=imdb_id).first()
    if movie and movie.slug:
        return redirect('movie_detail', slug=movie.slug)
    
    info_service = MovieInfoService()
    details = info_service.get_movie_details(imdb_id)
    
    if not details or not details.get('title'):
        return redirect('index')

    new_movie = Movie.objects.create(
        imdb_id=imdb_id,
        title=details['title'],
        movie_info=details,
        episode_data=[] 
    )
    
    return redirect('movie_detail', slug=new_movie.slug)

def movie_detail(request, slug):
    """Film detay sayfası (SEO Uyumlu URL)."""
    movie = get_object_or_404(Movie, slug=slug)
    return render(request, 'movie_detail.html', {
        'movie': movie,
        'imdb_id': movie.imdb_id,
        'movie_info': movie.movie_info or {'title': movie.title}
    })

def analyze_movie(request):
    """
    Gelişmiş Analiz Motoru:
    JavaScript tarafından çağrılır. Altyazı bulmak için 3 aşamalı hiyerarşi kullanır.
    """
    try:
        imdb_id = request.GET.get('imdb_id', '').strip()
        if not imdb_id:
            return JsonResponse({'error': 'ID gerekli.'}, status=400)

        movie_obj = Movie.objects.filter(imdb_id=imdb_id).first()
        
        # 1. Önbellek Kontrolü
        if movie_obj and movie_obj.episode_data:
             return JsonResponse({
                'source': 'Veritabanı',
                'episodes': movie_obj.episode_data,
                'movie_info': movie_obj.movie_info
            })

        info_service = MovieInfoService()
        sub_service = SubtitleService()
        ai_service = AIService()

        movie_info = movie_obj.movie_info if movie_obj else info_service.get_movie_details(imdb_id)
        
        # --- ALTYAZI TEMİN HİYERARŞİSİ ---
        raw_sub = ""
        source_label = ""

        if TEST_MODE:
            # TEST MODU: Sadece yerel dosya
            try:
                with open(os.path.join(settings.BASE_DIR, 'test.srt'), 'r', encoding='utf-8') as f:
                    raw_sub = f.read()
                source_label = "Yerel Test Dosyası"
            except FileNotFoundError:
                return JsonResponse({'error': 'test.srt bulunamadı.'}, status=500)
        else:
            # GERÇEK MOD: Zincirleme Arama
            # A: OpenSubtitles API dene
            raw_sub = sub_service.get_subtitle(imdb_id)
            source_label = "OpenSubtitles"

            # B: Bulunamazsa Subliminal (Multi-Provider) dene
            if not raw_sub:
                print("⚠️ OpenSubtitles bulamadı, Subliminal deneniyor...")
                raw_sub = sub_service.get_subtitle_alt(movie_info['title'])
                source_label = "Subliminal (Alternatif Kaynaklar)"

        if not raw_sub:
            return JsonResponse({'error': 'Hiçbir kaynakta uygun altyazı bulunamadı.'}, status=404)

        # --- AI ANALİZ ---
        clean_sub = ai_service.clean_subtitle(raw_sub)
        episodes = ai_service.split_movie_into_episodes(clean_sub)

        if isinstance(episodes, dict) and "error" in episodes:
             return JsonResponse({'error': episodes['error']}, status=500)

        # Sonucu Veritabanına Yaz
        if movie_obj:
            movie_obj.episode_data = episodes
            movie_obj.save()
        
        return JsonResponse({
            'source': source_label,
            'episodes': episodes,
            'movie_info': movie_info
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

def autocomplete_movies(request):
    """Canlı arama önerileri."""
    query = request.GET.get('q', '').strip()
    if len(query) < 3: return JsonResponse({'results': []})
    
    info_service = MovieInfoService()
    results = info_service.search_candidates(query)
    return JsonResponse({'results': results})