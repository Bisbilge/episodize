# views.py
import traceback
import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Movie
from .services import AIService, SubtitleService, MovieInfoService

# --- MOD AYARI ---
# True: API yerine 'test.srt' kullanır. 
# False: OpenSubtitles API kullanır.
TEST_MODE = True 

def index(request):
    """
    Ana Sayfa: Veritabanındaki filmleri listeler.
    Sadece başlığı ve slug'ı olan (hatasız) kayıtları getirir.
    """
    movies = Movie.objects.exclude(title__isnull=True).order_by('-created_at')
    return render(request, 'index.html', {'movies': movies})

def open_movie_by_id(request, imdb_id):
    """
    TRAFİK KONTROLÜ (Redirector):
    Kullanıcı ID ile gelirse (örn: arama kutusundan),
    önce veritabanında bu ID'ye ait bir Slug var mı bakar.
    Varsa o Slug'a yönlendirir.
    Yoksa 'Taslak' kayıt oluşturup Slug üretir ve oraya yönlendirir.
    """
    imdb_id = imdb_id.strip()
    
    # 1. Zaten kayıtlı mı?
    movie = Movie.objects.filter(imdb_id=imdb_id).first()
    if movie and movie.slug:
        return redirect('movie_detail', slug=movie.slug)
    
    # 2. Kayıtlı değil, önce ismini bulmamız lazım (Slug için)
    info_service = MovieInfoService()
    details = info_service.get_movie_details(imdb_id)
    
    if not details or not details.get('title'):
        # Film bulunamazsa ana sayfaya at veya hata göster
        return redirect('index')

    # 3. Yeni kayıt oluştur (Henüz bölüm verisi yok, boş liste)
    # save() metodu models.py'da otomatik slug üretecek.
    new_movie = Movie.objects.create(
        imdb_id=imdb_id,
        title=details['title'],
        movie_info=details, # Bilgileri cache'le
        episode_data=[] 
    )
    
    return redirect('movie_detail', slug=new_movie.slug)

def movie_detail(request, slug):
    """
    ASIL FİLM SAYFASI:
    URL artık '/the-matrix/' şeklinde görünür.
    Eğer 'episode_data' boşsa, HTML içindeki JS analizi başlatır.
    """
    movie = get_object_or_404(Movie, slug=slug)
    
    return render(request, 'movie_detail.html', {
        'movie': movie,
        'imdb_id': movie.imdb_id, # JS analizi için ID şart
        'movie_info': movie.movie_info or {'title': movie.title}
    })

def analyze_movie(request):
    """
    API UCU:
    Bu fonksiyon sadece JSON döner. HTML içindeki JS buraya istek atar.
    """
    try:
        user_input = request.GET.get('imdb_id', '').strip()
        if not user_input:
            return JsonResponse({'error': 'ID gerekli.'}, status=400)

        # ID'ye göre filmi bul (Zaten open_movie_by_id ile oluşturulmuş olmalı)
        movie_obj = Movie.objects.filter(imdb_id=user_input).first()
        
        # Eğer zaten analiz edildiyse tekrar yapma
        if movie_obj and movie_obj.episode_data:
             return JsonResponse({
                'source': 'Database Cache',
                'episodes': movie_obj.episode_data,
                'movie_info': movie_obj.movie_info
            })

        # --- ANALİZ SÜRECİ ---
        info_service = MovieInfoService()
        sub_service = SubtitleService()
        ai_service = AIService()

        movie_info = movie_obj.movie_info if movie_obj else info_service.get_movie_details(user_input)

        # Altyazı Temini
        raw_sub = ""
        if TEST_MODE:
            print("🧪 Test Modu: test.srt okunuyor...")
            try:
                with open(os.path.join(settings.BASE_DIR, 'test.srt'), 'r', encoding='utf-8') as f:
                    raw_sub = f.read()
            except FileNotFoundError:
                return JsonResponse({'error': 'test.srt bulunamadı.'}, status=500)
        else:
            try:
                raw_sub = sub_service.get_subtitle(user_input)
            except Exception as e:
                return JsonResponse({'error': f"Altyazı hatası: {str(e)}"}, status=404)

        # AI İşlemi
        clean_sub = ai_service.clean_subtitle(raw_sub)
        episodes = ai_service.split_movie_into_episodes(clean_sub)

        if isinstance(episodes, dict) and "error" in episodes:
             return JsonResponse({'error': episodes['error']}, status=500)

        # Sonucu Kaydet
        if movie_obj:
            movie_obj.episode_data = episodes
            movie_obj.save()
        
        return JsonResponse({
            'source': 'New Analysis',
            'episodes': episodes,
            'movie_info': movie_info
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

def autocomplete_movies(request):
    """Arama kutusu için öneriler"""
    query = request.GET.get('q', '').strip()
    if len(query) < 3: return JsonResponse({'results': []})
    
    info_service = MovieInfoService()
    results = info_service.search_candidates(query)
    return JsonResponse({'results': results})