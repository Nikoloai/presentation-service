import os
import json
import requests
import re
import hashlib
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from dotenv import load_dotenv
import uuid
import io
TRANSLATION_CACHE = {}
CYRILLIC_RE = re.compile('[а-яА-Я]')

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# API Keys from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
LIBRETRANSLATE_ENABLED = os.getenv('LIBRETRANSLATE_ENABLED', 'false').lower() in ('1', 'true', 'yes')
LIBRETRANSLATE_URL = os.getenv('LIBRETRANSLATE_URL', 'http://localhost:5001')
LIBRETRANSLATE_TIMEOUT = int(os.getenv('LIBRETRANSLATE_TIMEOUT', '10'))

# Configuration
OUTPUT_DIR = 'output'
IMAGE_CACHE_DIR = 'image_cache'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
if not os.path.exists(IMAGE_CACHE_DIR):
    os.makedirs(IMAGE_CACHE_DIR)


def translate_keyword_to_english(keyword, topic):
    """
    Translate/optimize keyword to concise English for Pexels using LibreTranslate (if enabled).
    Returns a 2-4 word English phrase. Uses in-memory cache.
    """
    try:
        if not keyword:
            return ''
        key = f"{topic}|{keyword}".lower()
        if key in TRANSLATION_CACHE:
            print(f"  🌐 LibreTranslate: '{keyword}' → '{TRANSLATION_CACHE[key]}' (from cache)")
            return TRANSLATION_CACHE[key]
        
        # If not enabled or keyword already English, return original
        if not LIBRETRANSLATE_ENABLED or not CYRILLIC_RE.search(keyword):
            return keyword
        
        payload = {
            'q': keyword,
            'source': 'ru',
            'target': 'en'
        }
        print(f"  🌐 LibreTranslate request: '{keyword}' → en at {LIBRETRANSLATE_URL}")
        resp = requests.post(f"{LIBRETRANSLATE_URL}/translate", json=payload, timeout=LIBRETRANSLATE_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            translated = data.get('translatedText', '').strip()
            # Sanitize minimal
            translated = re.sub(r'[^a-zA-Z\s]', '', translated)
            translated = ' '.join(translated.split())
            if translated:
                TRANSLATION_CACHE[key] = translated
                print(f"  ✓ LibreTranslate: '{keyword}' → '{translated}'")
                return translated
            else:
                print("  ⚠ LibreTranslate returned empty translation, using original")
                return keyword
        else:
            print(f"  ⚠ LibreTranslate error {resp.status_code}: {resp.text[:120]}... Using original")
            return keyword
    except Exception as e:
        print(f"  ⚠ LibreTranslate exception: {e}. Using original")
        return keyword


def detect_language(text):
    """
    Detect language: returns 'ru' if Cyrillic is present, else 'en'.
    """
    try:
        return 'ru' if CYRILLIC_RE.search(text or '') else 'en'
    except Exception:
        return 'en'


def generate_slide_content(topic, num_slides):
    """
    Generate slide content using OpenAI ChatGPT API with language support
    """
    try:
        # Detect language
        language = detect_language(topic)
        print(f"Detected language: {'Russian' if language == 'ru' else 'English'}")
        
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        if language == 'ru':
            prompt = f"""Создай структурированную презентацию на тему: "{topic}"
Количество слайдов: {num_slides}

ВАЖНО: Презентация должна состоять из ТЕЗИСОВ, а не описаний!

ТЕЗИС — это ключевое утверждение, которое раскрывает часть темы.
НЕ просто описывай, а формулируй конкретные идеи и аргументы.

СТРУКТУРА ТЕЗИСОВ:
- Слайд 1: Главная идея темы (основное утверждение)
- Слайды 2-{num_slides-1}: Ключевые аспекты, преимущества, применения
- Слайд {num_slides}: Заключение, будущее, вывод

Каждый тезис должен:
✓ Быть конкретным утверждением, специфичным для темы "{topic}"
✓ Содержать 2-3 точных предложения с КОНКРЕТНЫМИ деталями и примерами
✓ Развивать основную тему
✓ Образовывать логическую цепочку с другими тезисами
✓ ИЗБЕГАТЬ шаблонных фраз типа "ключевой фактор развития", "цифровая эпоха", "современное общество"
✓ Использовать СПЕЦИФИЧЕСКУЮ терминологию и факты, относящиеся именно к "{topic}"

Для каждого слайда верни JSON с полями:
- "title": Краткий заголовок (2-3 слова), специфичный для темы
- "search_keyword": Ключевые слова для поиска картинки на английском (3-4 слова)
- "content": ТЕЗИС — конкретное утверждение (2-3 предложения с деталями)

ПРИМЕР правильных тезисов для темы "Собаки":
{{
  "slides": [
    {{"title": "Эволюция собак", "search_keyword": "dog evolution wolf domestication", "content": "Собаки произошли от волков около 15 000 лет назад в процессе одомашнивания. Генетические исследования показывают, что первые собаки появились в Восточной Азии и распространились по всему миру вместе с человеком. Современные породы — результат селективного разведения последних 200 лет."}},
    {{"title": "Породы и их функции", "search_keyword": "dog breeds working dogs types", "content": "Существует более 400 признанных пород собак, каждая выведена для специфических задач. Пастушьи породы (бордер-колли, овчарки) управляют стадами, охотничьи (ретриверы, спаниели) помогают на охоте, а служебные (доберманы, ротвейлеры) охраняют территорию. Декоративные породы (чихуахуа, той-терьеры) выведены исключительно для компаньонства."}},
    {{"title": "Собачий интеллект", "search_keyword": "dog intelligence training cognition", "content": "Собаки способны запомнить до 165 слов и жестов, что сопоставимо с когнитивными способностями двухлетнего ребёнка. Бордер-колли считаются самой умной породой — они понимают новые команды после 5 повторений. Исследования показывают, что собаки различают человеческие эмоции по выражению лица и тону голоса."}}
  ]
}}

НЕПРАВИЛЬНО (шаблонные фразы):
"Собаки становятся ключевым фактором развития современного общества. Внедрение этих технологий открывает новые возможности."

ПРАВИЛЬНО (конкретные факты):
"Собаки обладают обонянием в 10 000 раз острее человеческого благодаря 300 миллионам обонятельных рецепторов. Это позволяет им обнаруживать наркотики, взрывчатку и даже диагностировать рак на ранних стадиях."

Возвращай ТОЛЬКО валидный JSON без дополнительного текста.

КРИТИЧЕСКИ ВАЖНО: 
- Каждый тезис должен содержать КОНКРЕТНЫЕ факты, цифры, примеры относящиеся к "{topic}"
- НЕ используй общие фразы про "технологии", "инновации", "будущее" без конкретики
- Заголовок и содержание слайда должны ЛОГИЧЕСКИ соответствовать друг другу
- Каждый search_keyword должен быть РАЗНЫМ и специфичным"""
        else:
            prompt = f"""Create a structured presentation on the topic: "{topic}"
Number of slides: {num_slides}

IMPORTANT: The presentation must consist of THESIS STATEMENTS, not descriptions!

THESIS — a key statement that reveals part of the topic.
Do NOT just describe, but formulate specific ideas and arguments.

THESIS STRUCTURE:
- Slide 1: Main idea of the topic (core statement)
- Slides 2-{num_slides-1}: Key aspects, benefits, applications
- Slide {num_slides}: Conclusion, future, takeaway

Each thesis must:
✓ Be a specific statement directly related to "{topic}"
✓ Contain 2-3 precise sentences with CONCRETE details and examples
✓ Develop the main topic
✓ Form a logical chain with other theses
✓ AVOID template phrases like "key technology", "digital age", "modern society"
✓ Use SPECIFIC terminology and facts relevant only to "{topic}"

For each slide, return JSON with fields:
- "title": Brief title (2-3 words) specific to the topic
- "search_keyword": Keywords for image search in English (3-4 words)
- "content": THESIS — specific statement (2-3 sentences with details)

EXAMPLE of correct theses for "Dogs":
{{
  "slides": [
    {{"title": "Dog Evolution", "search_keyword": "dog evolution wolf domestication", "content": "Dogs descended from wolves approximately 15,000 years ago through domestication. Genetic research shows that the first dogs appeared in East Asia and spread worldwide with humans. Modern breeds are the result of selective breeding over the past 200 years."}},
    {{"title": "Breeds and Functions", "search_keyword": "dog breeds working dogs types", "content": "Over 400 recognized dog breeds exist, each bred for specific tasks. Herding breeds (Border Collies, Shepherds) manage livestock, hunting breeds (Retrievers, Spaniels) assist in hunting, while guard breeds (Dobermans, Rottweilers) protect property. Toy breeds (Chihuahuas, Terriers) are bred exclusively for companionship."}},
    {{"title": "Canine Intelligence", "search_keyword": "dog intelligence training cognition", "content": "Dogs can memorize up to 165 words and gestures, comparable to the cognitive abilities of a two-year-old child. Border Collies are considered the smartest breed, understanding new commands after just 5 repetitions. Research shows dogs distinguish human emotions through facial expressions and tone of voice."}}
  ]
}}

WRONG (template phrases):
"Dogs are becoming a key factor in modern society. The adoption of these technologies unlocks new potential."

CORRECT (concrete facts):
"Dogs possess a sense of smell 10,000 times sharper than humans due to 300 million olfactory receptors. This enables them to detect drugs, explosives, and even diagnose cancer in early stages."

Return ONLY valid JSON without additional text.

CRITICAL: 
- Each thesis must contain CONCRETE facts, numbers, examples related to "{topic}"
- Do NOT use generic phrases about "technology", "innovation", "future" without specifics
- Title and content of each slide must be LOGICALLY connected
- Each search_keyword must be DIFFERENT and specific"""

        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'system', 'content': 'You are a helpful presentation creator. Always respond with valid JSON only.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 1500
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
        
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        
        # Try to parse JSON from response
        # Remove markdown code blocks if present
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip()
        
        slides_data = json.loads(content)
        return slides_data.get('slides', [])
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response content: {content}")
        # Fail instead of generating low-quality fallback
        return None
    except Exception as e:
        print(f"Error generating content: {e}")
        # Fail instead of generating low-quality fallback
        return None


def create_fallback_slides(topic, num_slides):
    """
    Create fallback slides if API fails with language support
    """
    language = detect_language(topic)
    slides = []
    
    if language == 'ru':
        slides.append({
            'title': f'{topic} изменяет мир',
            'search_keyword': f'{topic} innovation future technology',
            'content': f'{topic} становится ключевым фактором развития современного общества. Внедрение этих технологий открывает новые возможности для бизнеса и повседневной жизни. Понимание {topic} критически важно для успеха в цифровую эпоху.'
        })
        
        thesis_templates_ru = [
            ('Ключевые преимущества', 'key benefits advantages', lambda t: f'{t} повышает эффективность работы и снижает издержки. Автоматизация процессов позволяет сосредоточиться на стратегических задачах. Компании, внедрившие {t}, получают конкурентное преимущество на рынке.'),
            ('Практическое применение', 'real world practical use', lambda t: f'Реальные кейсы показывают эффективность {t} в различных отраслях. От медицины до финансов, технология решает сложные задачи. Успешные примеры вдохновляют на дальнейшее внедрение.'),
            ('Вызовы и решения', 'challenges solutions problems', lambda t: f'Основные препятствия при внедрении {t} включают технические и организационные барьеры. Однако современные подходы позволяют эффективно преодолевать эти трудности. Правильная стратегия минимизирует риски и ускоряет адаптацию.'),
            ('Будущее технологии', 'future innovation development', lambda t: f'{t} будет играть всё более важную роль в ближайшие годы. Инвестиции в развитие этой области растут экспоненциально. Те, кто освоит {t} сегодня, станут лидерами завтрашнего дня.')
        ]
        
        for i in range(1, min(num_slides, len(thesis_templates_ru) + 1)):
            title, keywords, content_func = thesis_templates_ru[i - 1]
            slides.append({
                'title': title,
                'search_keyword': f'{topic} {keywords}',
                'content': content_func(topic)
            })
    else:
        slides.append({
            'title': f'{topic} Revolution',
            'search_keyword': f'{topic} innovation future technology',
            'content': f'{topic} is reshaping how we approach modern challenges and opportunities. The adoption of these technologies unlocks new potential for businesses and daily life. Mastering {topic} is critical for success in the digital age.'
        })
        
        thesis_templates_en = [
            ('Key Advantages', 'key benefits advantages', lambda t: f'{t} dramatically improves efficiency while reducing operational costs. Automation enables teams to focus on strategic initiatives instead of routine tasks. Organizations implementing {t} gain significant competitive advantages in their markets.'),
            ('Real-World Impact', 'real world practical applications', lambda t: f'Success stories demonstrate the effectiveness of {t} across diverse industries. From healthcare to finance, the technology solves previously intractable problems. These proven examples inspire further adoption and innovation.'),
            ('Overcoming Challenges', 'challenges solutions problems', lambda t: f'Primary obstacles to {t} adoption include technical complexity and organizational resistance. Modern frameworks and methodologies effectively address these barriers. Strategic planning minimizes risks and accelerates successful implementation.'),
            ('Future Outlook', 'future innovation development', lambda t: f'{t} will play an increasingly vital role in shaping tomorrow. Investment in this field is growing exponentially year over year. Early adopters of {t} position themselves as leaders of the future.')
        ]
        
        for i in range(1, min(num_slides, len(thesis_templates_en) + 1)):
            title, keywords, content_func = thesis_templates_en[i - 1]
            slides.append({
                'title': title,
                'search_keyword': f'{topic} {keywords}',
                'content': content_func(topic)
            })
    
    return slides


def get_cached_image_path(keywords):
    """
    Get cached image path based on keyword hash
    """
    cache_key = hashlib.md5(keywords.encode('utf-8')).hexdigest()
    cache_file = os.path.join(IMAGE_CACHE_DIR, f"{cache_key}.jpg")
    
    if os.path.exists(cache_file):
        print(f"  ⚡ Using cached image for '{keywords}'")
        return cache_file
    
    return None


def save_image_to_cache(image_data, keywords):
    """
    Save downloaded image to cache
    """
    try:
        cache_key = hashlib.md5(keywords.encode('utf-8')).hexdigest()
        cache_file = os.path.join(IMAGE_CACHE_DIR, f"{cache_key}.jpg")
        
        with open(cache_file, 'wb') as f:
            f.write(image_data.getvalue())
        
        return cache_file
    except Exception as e:
        print(f"  ⚠ Error caching image: {e}")
        return None


def search_image(query):
    """
    Search for an image using Pexels API
    """
    try:
        # Clean and optimize search query
        query = query.strip().lower()
        
        headers = {
            'Authorization': PEXELS_API_KEY
        }
        
        params = {
            'query': query,
            'per_page': 1,
            'orientation': 'landscape'
        }
        
        print(f"  → Pexels search query: '{query}'")
        
        response = requests.get(
            'https://api.pexels.com/v1/search',
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"  ✗ Pexels API error: {response.status_code}")
            return None
        
        data = response.json()
        
        if data.get('photos') and len(data['photos']) > 0:
            # Get the large image URL
            image_url = data['photos'][0]['src']['large']
            print(f"  ✓ Image found: {data['photos'][0]['photographer']}")
            return image_url
        else:
            print(f"  ✗ No images found for query: '{query}'")
        
        return None
        
    except Exception as e:
        print(f"  ✗ Error searching image: {e}")
        return None


def search_image_with_fallback(search_keyword, slide_title, main_topic, used_images):
    """
    Search for image with multiple fallback attempts
    Returns: (image_data, image_url) or (None, None)
    """
    attempts = []
    translated = None
    if CYRILLIC_RE.search(search_keyword or ''):
        translated = translate_keyword_to_english(search_keyword, main_topic)
        if translated:
            print(f"  Search keyword: '{translated}'")
            attempts.append((translated, "Translated keyword"))
            first_word = translated.split()[0] if translated else ''
            if first_word:
                attempts.append((first_word, "First word"))
    else:
        if search_keyword:
            print(f"  Search keyword: '{search_keyword}'")
            attempts.append((search_keyword, "Original keyword"))
    
    attempts.extend([
        (slide_title, "Slide title"),
        (main_topic, "Main topic")
    ])
    
    for query, attempt_name in attempts:
        if not query or query.strip() == "":
            continue
            
        print(f"  → Attempt: {attempt_name} - '{query}'")
        
        # Check cache first
        cached_path = get_cached_image_path(query)
        if cached_path and cached_path not in used_images:
            try:
                with open(cached_path, 'rb') as f:
                    image_data = io.BytesIO(f.read())
                return image_data, cached_path
            except:
                pass
        
        # Search on Pexels
        image_url = search_image(query)
        
        if image_url and image_url not in used_images:
            image_data = download_image(image_url)
            
            if image_data:
                # Save to cache
                cached_path = save_image_to_cache(image_data, query)
                return image_data, image_url
    
    print(f"  ✗ No unique image found after all attempts")
    return None, None


def is_libretranslate_available():
    try:
        if not LIBRETRANSLATE_ENABLED:
            return False
        resp = requests.get(f"{LIBRETRANSLATE_URL}/languages", timeout=LIBRETRANSLATE_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def download_image(url):
    """
    Download image from URL and return as bytes
    Security: Limit image size to prevent memory issues
    """
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB limit
    
    try:
        response = requests.get(url, timeout=10, stream=True)
        if response.status_code == 200:
            # Check content length if available
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > MAX_IMAGE_SIZE:
                print(f"  ⚠ Image too large: {content_length} bytes")
                return None
            
            # Download with size limit
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > MAX_IMAGE_SIZE:
                    print(f"  ⚠ Image exceeds size limit")
                    return None
            
            return io.BytesIO(content)
        return None
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None


def calculate_title_font_size(text, max_width_inches=8.5, bold=True):
    """
    Calculate optimal font size for title to fit in one line.
    Tries sizes from 40pt down to 24pt.
    Returns the largest font size that fits the text in one line.
    
    Approximate calculation: 1 character ≈ 0.6 * font_size_pt / 72 inches (for bold text)
    """
    # Font sizes to try in descending order
    font_sizes = [40, 36, 32, 28, 24]
    
    # Approximate character width factor for bold fonts (empirical)
    # For bold fonts: ~0.55-0.65 of font size in points
    char_width_factor = 0.6 if bold else 0.5
    
    for font_size in font_sizes:
        # Estimate text width in inches
        # char_width_in_points = font_size * char_width_factor
        # char_width_in_inches = char_width_in_points / 72
        estimated_width = len(text) * (font_size * char_width_factor / 72)
        
        if estimated_width <= max_width_inches:
            print(f"  📏 Title font size: {font_size}pt (estimated width: {estimated_width:.2f}in vs max {max_width_inches}in)")
            return font_size
    
    # If even 24pt doesn't fit, return 24pt anyway (minimum)
    print(f"  ⚠ Title very long, using minimum font size: 24pt")
    return 24


def create_presentation(topic, slides_data):
    """
    Create PowerPoint presentation with text and images
    """
    print(f"\n{'#'*60}")
    print(f"# Creating presentation: {topic}")
    print(f"# Total slides: {len(slides_data)}")
    print(f"{'#'*60}\n")
    
    # Create presentation object
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(5.625)
    
    # Track used images to avoid duplicates
    used_images = set()
    
    for idx, slide_data in enumerate(slides_data):
        # Add a blank slide
        blank_layout = prs.slide_layouts[6]  # Blank layout
        slide = prs.slides.add_slide(blank_layout)
        
        # Set background color
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(245, 245, 250)
        
        # Add title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3),
            Inches(8.5), Inches(0.8)
        )
        # Title style
        title_frame = title_box.text_frame
        title_frame.word_wrap = False  # NO line breaks - single line only
        title_frame.text = slide_data['title']
        title_para = title_frame.paragraphs[0]
        title_para.alignment = PP_ALIGN.CENTER
        
        is_title_slide = (idx == 0)
        is_last_slide = (idx == len(slides_data) - 1)
        
        # Calculate optimal font size to fit title in one line
        optimal_font_size = calculate_title_font_size(
            text=slide_data['title'],
            max_width_inches=8.5,
            bold=True
        )
        
        if is_title_slide or is_last_slide:
            # Dark background
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(15, 25, 45)
            
            title_para.font.size = Pt(optimal_font_size)
            title_para.font.bold = True
            title_para.font.color.rgb = RGBColor(255, 255, 255)
        else:
            # Light background with blue vertical bar
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(245, 245, 250)
            
            title_para.font.size = Pt(optimal_font_size)
            title_para.font.bold = True
            title_para.font.color.rgb = RGBColor(30, 60, 120)
            
            # Left vertical blue line
            try:
                slide.shapes.add_shape(
                    MSO_AUTO_SHAPE_TYPE.RECTANGLE,
                    Inches(0.3), Inches(0.3), Inches(0.1), Inches(5.0)
                ).fill.fore_color.rgb = RGBColor(30, 60, 180)
            except Exception as e:
                print(f"  ⚠ Failed to add left bar: {e}")
        
        # Search and add image using specific keyword with fallback
        search_term = slide_data.get('search_keyword', slide_data['title'])
        print(f"\n[Slide {idx + 1}/{len(slides_data)}] {slide_data['title']}")
        print(f"  Content: {slide_data['content'][:60]}...")
        
        image_data, image_url = search_image_with_fallback(
            search_keyword=search_term,
            slide_title=slide_data['title'],
            main_topic=topic,
            used_images=used_images
        )
        
        if image_data and image_url:
            # Mark image as used
            used_images.add(image_url)
            
            try:
                # Add image on the right side
                slide.shapes.add_picture(
                    image_data,
                    Inches(5.5), Inches(1.3),
                    width=Inches(4),
                    height=Inches(3.5)
                )
                print(f"  ✓ Image added to slide (unique)")
            except Exception as e:
                print(f"  ✗ Error adding image to slide: {e}")
        else:
            print(f"  ⚠ Continuing without image (no unique image found)")
        
        # Add content text (description)
        content_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(1.4),
            Inches(4.8), Inches(3.6)
        )
        content_frame = content_box.text_frame
        content_frame.word_wrap = True
        content_frame.text = slide_data['content']
        
        # Format content text
        for paragraph in content_frame.paragraphs:
            paragraph.font.size = Pt(16 if not (is_title_slide or is_last_slide) else 20)
            paragraph.font.color.rgb = RGBColor(40, 40, 40) if not (is_title_slide or is_last_slide) else RGBColor(255, 255, 255)
            paragraph.space_after = Pt(10)
            paragraph.line_spacing = 1.2
        
        print(f"\n{'='*60}")
        print(f"✓ Slide {idx + 1} created successfully")
        print(f"  Title: {slide_data['title']}")
        print(f"  Content length: {len(slide_data['content'])} characters")
        print(f"{'='*60}")
    
    # Save presentation
    filename = f"presentation_{uuid.uuid4().hex[:8]}.pptx"
    filepath = os.path.join(OUTPUT_DIR, filename)
    prs.save(filepath)
    
    print(f"\n{'#'*60}")
    print(f"# ✓ Presentation created successfully!")
    print(f"# File: {filename}")
    print(f"# Location: {filepath}")
    print(f"{'#'*60}\n")
    
    return filepath


@app.route('/')
def index():
    """
    Render main page
    """
    return render_template('index.html')


@app.route('/api/create-presentation', methods=['POST'])
def create_presentation_api():
    """
    API endpoint to create presentation
    """
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        num_slides = data.get('num_slides', 5)
        
        # Validation
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        if not isinstance(num_slides, int) or num_slides < 3 or num_slides > 10:
            return jsonify({'error': 'Number of slides must be between 3 and 10'}), 400
        
        # Check API keys
        if not OPENAI_API_KEY:
            return jsonify({'error': 'OpenAI API key not configured'}), 500
        
        if not PEXELS_API_KEY:
            return jsonify({'error': 'Pexels API key not configured'}), 500
        
        # Generate slide content
        print(f"Generating content for topic: {topic}, slides: {num_slides}")
        slides_data = generate_slide_content(topic, num_slides)
        
        if not slides_data:
            return jsonify({'error': 'Failed to generate slide content via OpenAI'}), 502
        
        # Ensure we have the right number of slides
        slides_data = slides_data[:num_slides]
        
        # Create presentation
        print("Creating presentation...")
        filepath = create_presentation(topic, slides_data)
        
        return jsonify({
            'success': True,
            'filename': os.path.basename(filepath),
            'slides': slides_data
        })
        
    except Exception as e:
        print(f"Error in create_presentation_api: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<filename>')
def download_presentation(filename):
    """
    Download generated presentation
    Security: Prevent path traversal attacks
    """
    try:
        # Security: Normalize path and prevent directory traversal
        filename = os.path.basename(filename)  # Remove any path components
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Security: Ensure file is within OUTPUT_DIR
        if not os.path.abspath(filepath).startswith(os.path.abspath(OUTPUT_DIR)):
            return jsonify({'error': 'Access denied'}), 403
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting Presentation Service...")
    print(f"OpenAI API Key configured: {bool(OPENAI_API_KEY)}")
    print(f"Pexels API Key configured: {bool(PEXELS_API_KEY)}")
    print(f"LibreTranslate enabled: {LIBRETRANSLATE_ENABLED}")
    print(f"LibreTranslate URL: {LIBRETRANSLATE_URL}")
    print(f"LibreTranslate reachable: {is_libretranslate_available()}")
    app.run(debug=True, host='0.0.0.0', port=5000)
