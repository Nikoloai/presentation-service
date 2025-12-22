# CLIP Integration Guide

## Обзор (Overview)

Интеграция CLIP (Contrastive Language-Image Pre-training) добавляет семантический поиск изображений на основе AI, что значительно улучшает подбор картинок для слайдов.

**CLIP integration adds AI-powered semantic image search, dramatically improving image relevance for slides.**

---

## Что изменилось (What Changed)

### 1. Новые зависимости (New Dependencies)

Добавлены в `requirements.txt`:
```
torch>=2.0.0
torchvision>=0.15.0
transformers>=4.30.0
sentence-transformers>=2.2.0
Pillow>=10.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
```

### 2. Новые модули (New Modules)

#### `services/clip_client.py`
Сервис для работы с CLIP моделью:
- `is_clip_available()` - проверка доступности CLIP
- `get_text_embedding(text)` - получение эмбеддинга для текста
- `get_image_embedding(image_url)` - получение эмбеддинга для изображения (опционально)
- `compute_similarity(emb1, emb2)` - вычисление косинусного сходства
- Встроенное кэширование эмбеддингов для производительности

**Features:**
- Lazy model loading (one-time initialization)
- In-memory embedding cache (up to 1000 entries)
- Graceful fallback if CLIP unavailable
- Using `clip-ViT-B-32` model (balanced speed/quality)

#### `services/image_matcher.py`
Семантический подбор изображений:
- `pick_best_image_for_slide()` - основная функция подбора
- `rank_images_by_relevance()` - ранжирование кандидатов
- `get_similarity_for_image()` - проверка сходства (для отладки)

**Algorithm:**
1. Combine slide title + content into semantic context
2. Get CLIP embedding for context
3. Get embeddings for all candidate images (via descriptions)
4. Compute cosine similarity for each candidate
5. Return image with highest similarity above threshold (0.25 default)
6. If all below threshold, return None (avoids poor matches)

### 3. Изменения в app.py

#### Импорты (Imports)
```python
# CLIP services for semantic image matching
try:
    from services.clip_client import is_clip_available, get_text_embedding
    from services.image_matcher import pick_best_image_for_slide as clip_pick_best_image
    CLIP_ENABLED = True
except ImportError:
    CLIP_ENABLED = False
    clip_pick_best_image = None
```

#### Обновлена функция `search_image_for_slide()`
Теперь работает в два этапа:

**Этап 1: CLIP-enhanced search (если доступен)**
- Получает 10-15 кандидатов изображений по ключевым словам
- Применяет семантический матчинг через CLIP
- Выбирает наиболее релевантное изображение

**Этап 2: Fallback (если CLIP недоступен или не нашёл подходящее)**
- Использует традиционный поиск по ключевым словам
- Сохраняет обратную совместимость

---

## Установка (Installation)

### 1. Установить зависимости

```bash
pip install -r requirements.txt
```

**Важно:** Установка PyTorch может занять время (~2GB скачивания).

**Для GPU поддержки (опционально):**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 2. Первый запуск

При первом запуске CLIP модель скачается автоматически (~600MB):
```
🔄 Loading CLIP model (this may take a minute on first run)...
✅ CLIP model loaded successfully
   → Model: clip-ViT-B-32
   → Embedding dimension: 512
```

Модель кэшируется локально в `~/.cache/torch/sentence_transformers/`.

---

## Использование (Usage)

### Автоматическое использование

CLIP интегрирован в существующий процесс генерации презентаций. Никаких изменений в API не требуется!

При создании презентации в логах будет:
```
🔍 Searching image for slide: 'Revenue Growth Analysis'
  🎯 Keywords extracted: ['revenue', 'growth', 'analysis']
  🤖 Using CLIP semantic matching for better relevance
  📊 Found 15 candidates, applying CLIP ranking...
     [1] Business chart showing financial growth → 0.782
     [2] Professional business team in office   → 0.543
     [3] Mountain landscape with sunset         → 0.234
  ✅ CLIP selected best match: https://images.pexels.com/...
```

### Конфигурация порога (Threshold Configuration)

В `app.py`, функция `search_image_for_slide()`:
```python
best_image = clip_pick_best_image(
    slide_title=slide_title,
    slide_content=slide_content,
    image_candidates=candidates,
    exclude_images=exclude_images,
    similarity_threshold=0.25  # Изменить здесь
)
```

**Рекомендации:**
- `0.15-0.25` - более мягкий порог (больше изображений принимается)
- `0.25-0.35` - стандартный порог (баланс качества/количества)
- `0.35-0.50` - строгий порог (только очень релевантные)

### Ручное использование

```python
from services.clip_client import get_text_embedding, compute_similarity

# Получить эмбеддинги
text_emb = get_text_embedding("Financial growth chart")
image_desc_emb = get_text_embedding("Business revenue statistics")

# Вычислить сходство
similarity = compute_similarity(text_emb, image_desc_emb)
print(f"Similarity: {similarity:.3f}")  # 0.0 - 1.0
```

---

## Тестирование (Testing)

### Запуск всех тестов

```bash
# Тесты CLIP client
python -m pytest tests/test_clip_client.py -v

# Тесты image matcher
python -m pytest tests/test_image_matcher.py -v

# Все тесты
python -m pytest tests/ -v
```

### Быстрый тест

```bash
# Тест CLIP matcher с примером
python -m services.image_matcher
```

Вывод:
```
============================================================
Testing CLIP Image Matcher
============================================================

Slide: 'Revenue Growth Analysis'
Content: Our Q4 2024 financial results show a 45% increase in revenue...

Testing semantic matching...

  🤖 CLIP semantic matching for: 'Revenue Growth Analysis'
     [1] Business chart showing financial growth → 0.823
     [2] Professional business team working      → 0.542
     [3] Beautiful mountain landscape            → 0.187

✅ Best match selected:
   URL: https://example.com/chart.jpg
   Description: Business chart showing financial growth

============================================================
```

---

## Производительность (Performance)

### Кэширование

CLIP использует два уровня кэширования:

1. **Кэш эмбеддингов** (in-memory)
   - До 1000 записей
   - Автоматическое удаление старых
   - Проверка: `clip_client.get_cache_stats()`

2. **Кэш модели** (диск)
   - Модель скачивается один раз
   - Хранится в `~/.cache/torch/sentence_transformers/`
   - Ленивая загрузка (при первом использовании)

### Время выполнения

**Первый запуск (с загрузкой модели):**
- Загрузка модели: ~30-60 секунд
- Обработка слайда: ~2-3 секунды (15 кандидатов)

**Последующие запуски:**
- Обработка слайда: ~1-2 секунды (с кэшем)
- Без кэша: ~2-3 секунды

**На GPU (если доступен):**
- Обработка слайда: ~0.5-1 секунда

### Оптимизация

Для улучшения производительности:

1. Уменьшить количество кандидатов:
```python
candidate_count = 10  # вместо 15
```

2. Использовать GPU (если доступен):
```python
# PyTorch автоматически использует GPU если доступен
# Проверка: torch.cuda.is_available()
```

---

## Graceful Degradation (Обработка ошибок)

CLIP интегрирован с умным fallback'ом:

### Сценарий 1: CLIP недоступен (зависимости не установлены)
```
⚠️ CLIP services not available: No module named 'torch'
   → Install dependencies: pip install torch sentence-transformers
```
→ Использует традиционный поиск по ключевым словам

### Сценарий 2: Модель не загружается
```
❌ Failed to load CLIP model: Connection timeout
```
→ Автоматический fallback на keyword search

### Сценарий 3: Все кандидаты ниже порога
```
⚠️ CLIP found no suitable match (below threshold or all excluded)
🔍 Falling back to traditional keyword search
```
→ Попытка найти через обычный поиск

### Сценарий 4: Нет кандидатов
```
⚠️ No image candidates found
🔍 Falling back to traditional keyword search
```
→ Стандартный поиск с fallback логикой

**Результат:** Система НИКОГДА не падает из-за CLIP, всегда есть fallback!

---

## Архитектура (Architecture)

```
┌─────────────────────────────────────────────────────┐
│  app.py (create_presentation)                       │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  search_image_for_slide()                    │  │
│  │                                               │  │
│  │  1. Extract keywords from slide              │  │
│  │  2. Check if CLIP available                  │  │
│  │     ┌─────────────────────────┐              │  │
│  │     │ YES → CLIP Path         │              │  │
│  │     │                          │              │  │
│  │     │ • Fetch 15 candidates    │              │  │
│  │     │ • Apply semantic match   │ ────────┐   │  │
│  │     │ • Pick best by CLIP      │         │   │  │
│  │     └─────────────────────────┘         │   │  │
│  │                                          │   │  │
│  │     ┌─────────────────────────┐         │   │  │
│  │     │ NO → Keyword Path       │         │   │  │
│  │     │                          │         │   │  │
│  │     │ • Traditional search     │         │   │  │
│  │     │ • First matching image   │         │   │  │
│  │     └─────────────────────────┘         │   │  │
│  │                                          │   │  │
│  │  3. Return (image_data, url, query)     │   │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                                                │
                ┌───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────┐
│  services/image_matcher.py                            │
│                                                        │
│  pick_best_image_for_slide()                          │
│  │                                                     │
│  ├─ 1. Combine slide title + content                  │
│  ├─ 2. Get CLIP embedding for context ────────────┐   │
│  ├─ 3. For each candidate:                        │   │
│  │    • Get embedding for description             │   │
│  │    • Compute similarity                        │   │
│  ├─ 4. Sort by similarity (descending)            │   │
│  ├─ 5. Filter by threshold (0.25)                 │   │
│  └─ 6. Return best match or None                  │   │
└───────────────────────────────────────────────────────┘
                                                    │
                ┌───────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────┐
│  services/clip_client.py                              │
│                                                        │
│  • _clip_model (lazy loaded, singleton)               │
│  • _embedding_cache (dict, max 1000)                  │
│                                                        │
│  get_text_embedding(text)                             │
│  │                                                     │
│  ├─ 1. Check cache                                    │
│  ├─ 2. If miss: encode with CLIP                      │
│  ├─ 3. L2 normalize                                   │
│  ├─ 4. Cache result                                   │
│  └─ 5. Return numpy array (512,)                      │
│                                                        │
│  compute_similarity(emb1, emb2)                       │
│  └─ Dot product (embeddings are normalized)           │
└───────────────────────────────────────────────────────┘
```

---

## Отладка (Debugging)

### Проверить доступность CLIP

```python
from services.clip_client import is_clip_available

if is_clip_available():
    print("✅ CLIP ready!")
else:
    print("❌ CLIP not available")
```

### Проверить кэш

```python
from services.clip_client import get_cache_stats

stats = get_cache_stats()
print(f"Cache size: {stats['size']}/{stats['max_size']}")
```

### Очистить кэш

```python
from services.clip_client import clear_cache
clear_cache()
```

### Проверить сходство вручную

```python
from services.image_matcher import get_similarity_for_image

score = get_similarity_for_image(
    slide_title="Revenue Growth",
    slide_content="Financial results Q4",
    image_description="Business chart with increasing revenue"
)
print(f"Similarity: {score:.3f}")
```

---

## FAQ

### Q: Нужен ли GPU для CLIP?
**A:** Нет, CPU достаточно. GPU ускорит обработку (~2-3x быстрее), но не обязателен.

### Q: Сколько места занимает модель?
**A:** ~600MB для `clip-ViT-B-32` модели.

### Q: Можно ли использовать другую CLIP модель?
**A:** Да, измените в `services/clip_client.py`:
```python
_clip_model = SentenceTransformer('clip-ViT-L-14')  # Больше, точнее
# или
_clip_model = SentenceTransformer('clip-ViT-B-16')  # Компромисс
```

### Q: Что делать если CLIP слишком медленный?
**A:** 
1. Уменьшите `candidate_count` с 15 до 10
2. Увеличьте порог `similarity_threshold` до 0.3-0.4
3. Используйте GPU если доступен

### Q: Почему CLIP выбирает "неправильные" изображения?
**A:**
1. Проверьте описания кандидатов (может быть плохое качество метаданных)
2. Увеличьте `similarity_threshold` (строже фильтрация)
3. Проверьте качество slide_content (больше контекста = лучше результат)

### Q: Можно ли отключить CLIP для конкретных презентаций?
**A:** Да, установите переменную окружения:
```bash
CLIP_ENABLED=false
```
Или в коде временно:
```python
CLIP_ENABLED = False  # в app.py
```

---

## Roadmap (Будущие улучшения)

### Planned Features:
1. **Image embedding caching** - кэширование эмбеддингов самих изображений (не только описаний)
2. **Fine-tuned threshold** - автоматическая настройка порога по feedback
3. **Multi-modal search** - комбинирование текста и визуальных признаков
4. **Redis caching** - распределённое кэширование для масштабирования
5. **A/B testing** - сравнение CLIP vs keyword для оценки улучшений

### Contributions Welcome!
Идеи и PR приветствуются в репозитории проекта.

---

## Troubleshooting

### Проблема: ModuleNotFoundError: No module named 'torch'
**Решение:**
```bash
pip install torch torchvision sentence-transformers
```

### Проблема: CLIP model download timeout
**Решение:**
```bash
# Скачать модель вручную
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('clip-ViT-B-32')"
```

### Проблема: Out of memory при загрузке модели
**Решение:**
- Закрыть другие приложения
- Использовать меньшую модель (`clip-ViT-B-16`)
- Увеличить swap память

### Проблема: Слишком медленно на CPU
**Решение:**
1. Уменьшить `candidate_count`
2. Включить кэширование (по умолчанию включено)
3. Использовать GPU или более быстрый CPU

---

## Контакты и поддержка

При возникновении проблем:
1. Проверьте логи при запуске приложения
2. Запустите тесты: `python -m pytest tests/ -v`
3. Проверьте версии зависимостей: `pip list | grep -E "torch|sentence"`
4. Создайте issue с подробным описанием проблемы

---

**Версия:** 1.0.0  
**Дата:** 2024-12-21  
**Автор:** AI SlideRush Team
