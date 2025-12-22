# Railway Deployment - Configuration Guide

## Переменные окружения для Railway

Добавьте следующие переменные в Railway Dashboard → Variables:

### 🤖 CLIP Configuration (обязательно)

```bash
# Включить CLIP семантический поиск
CLIP_ENABLED=true

# Порог схожести (0.25-0.40 рекомендуется)
# Выше = строже фильтрация, меньше "случайных" картинок
CLIP_SIMILARITY_THRESHOLD=0.30

# Минимум кандидатов для CLIP
CLIP_MIN_CANDIDATES=8

# Максимум кандидатов для ранжирования
CLIP_MAX_CANDIDATES=20
```

### 🌐 Translation Configuration (универсальный слой)

```bash
# Отключить перевод для поиска картинок (рекомендуется с CLIP)
TRANSLATION_ENABLED=false

# Провайдер перевода: none, libre, external
TRANSLATION_PROVIDER=none

# Целевой язык для поиска картинок (обычно 'en')
TRANSLATION_TARGET_LANG=en
```

**Почему отключать перевод:**
- CLIP понимает семантику на любом языке (русский, английский)
- Pexels/Unsplash индексируют картинки мультиязычно
- Исключает ошибки Connection refused от LibreTranslate
- Упрощает конфигурацию и ускоряет генерацию

**Когда включать перевод:**
- Если у вас стабильный LibreTranslate (`TRANSLATION_PROVIDER=libre`)
- Если подключён внешний API (`TRANSLATION_PROVIDER=external`)
- Если явно нужен перевод запросов в английский

---

## Что изменилось

### 1. **CLIP теперь читается из окружения**
- `CLIP_ENABLED` - включает/выключает CLIP
- При старте выводится подробный лог инициализации CLIP
- Если CLIP недоступен, автоматический fallback на keyword search

### 2. **Настраиваемый threshold**
- `CLIP_SIMILARITY_THRESHOLD=0.30` (по умолчанию)
- Значения:
  - `0.20-0.25` = мягкий (больше картинок)
  - `0.30-0.35` = **рекомендуется** (баланс)
  - `0.40+` = строгий (только очень релевантные)

### 3. **Минимум кандидатов**
- `CLIP_MIN_CANDIDATES=8` (по умолчанию)
- Если найдено меньше картинок → пропускает CLIP, использует keyword search
- Избегает плохих результатов при малом выборе

### 4. **Универсальный слой перевода**
- `TRANSLATION_ENABLED` - главный флаг
- `TRANSLATION_PROVIDER` - выбор провайдера: `none`, `libre`, `external`
- `TRANSLATION_TARGET_LANG` - целевой язык (обычно `en`)
- При `TRANSLATION_ENABLED=false` или `TRANSLATION_PROVIDER=none` → перевод не выполняется
- При `TRANSLATION_PROVIDER=libre` → использует LibreTranslate
- При `TRANSLATION_PROVIDER=external` → использует внешний API (Google Translate, DeepL)
- Полная обратная совместимость с существующим кодом

---

## Примеры логов

### ✅ Успешный случай (CLIP работает)

```
==================================================
🤖 CLIP CONFIGURATION
==================================================
CLIP_ENABLED (from env): True
CLIP_SIMILARITY_THRESHOLD: 0.30
CLIP_MIN_CANDIDATES: 8
CLIP_MAX_CANDIDATES: 20
🔄 Attempting CLIP initialization...
✅ CLIP initialized successfully
   → Model: clip-ViT-B-32
   → Device: cpu
   → Embedding dimension: 512

🎯 Final CLIP status: ACTIVE
==================================================

🔍 Searching image for slide: 'Revenue Growth Analysis'
  🎯 Keywords extracted: ['revenue', 'growth', 'analysis']
  🤖 Using CLIP semantic matching for better relevance
     Threshold: 0.30, Min candidates: 8
  📊 Found 15 candidates, applying CLIP ranking...
  📝 CLIP context: 'Revenue Growth Analysis. Our Q4 revenue increased...'

  🏆 Top 3 candidates:
     [1] Business chart showing revenue     → 0.782 (Pexels)
     [2] Professional team in office        → 0.543 (Unsplash)
     [3] Mountain landscape sunset          → 0.187 (Pexels)

  ✅ Best match: 'Business chart showing revenue' (similarity: 0.782)

  ✅ CLIP selected: https://images.pexels.com/... (similarity=0.782, source=Pexels)
```

### ❌ Картинка пропущена (низкий similarity)

```
🔍 Searching image for slide: 'Основные идеи'
  🎯 Keywords extracted: ['основные', 'идеи']
  🤖 Using CLIP semantic matching for better relevance
     Threshold: 0.30, Min candidates: 8
  📊 Found 12 candidates, applying CLIP ranking...
  📝 CLIP context: 'Основные идеи. Краткое описание...'

  🏆 Top 3 candidates:
     [1] Abstract geometric pattern         → 0.234 (Pexels)
     [2] Office desk with laptop            → 0.198 (Unsplash)
     [3] Mountain hiking trail              → 0.156 (Pexels)

  ❌ Best match (0.234) below threshold (0.30)

  ❌ CLIP skipped (best similarity < 0.30 threshold)
     Reason: No image passed semantic relevance threshold
  🔍 Falling back to traditional keyword search
  ❌ No suitable image found (all options exhausted or duplicates)
```

### ℹ️ CLIP отключён

```
==================================================
🤖 CLIP CONFIGURATION
==================================================
CLIP_ENABLED (from env): False
CLIP_SIMILARITY_THRESHOLD: 0.30
CLIP_MIN_CANDIDATES: 8
CLIP_MAX_CANDIDATES=20
⚠️ CLIP disabled via CLIP_ENABLED=false
   → Using keyword search only

🎯 Final CLIP status: INACTIVE
==================================================

🔍 Searching image for slide: 'Market Analysis'
  🎯 Keywords extracted: ['market', 'analysis']
  ℹ️ CLIP disabled (CLIP_ENABLED=false)
     Using keyword search only
  🔍 Falling back to traditional keyword search
  ✅ Found unique image: https://images.pexels.com/...
```

---

## Troubleshooting на Railway

### Проблема: CLIP не инициализируется

**Симптомы:**
```
❌ CLIP initialization failed - model not available
```

**Решение:**
1. Проверьте логи Railway на наличие ошибок установки зависимостей
2. Убедитесь что `requirements.txt` содержит:
   ```
   torch>=2.0.0
   sentence-transformers>=2.2.0
   ```
3. Если ошибка persist, временно отключите: `CLIP_ENABLED=false`

### Проблема: LibreTranslate Connection refused

**Симптомы:**
```
⚠ LibreTranslate connection error: Connection refused localhost:5001
```

**Решение:**
Добавьте в Railway Variables:
```
TRANSLATION_ENABLED=false
```

### Проблема: Много "случайных" картинок

**Решение:**
Увеличьте threshold:
```
CLIP_SIMILARITY_THRESHOLD=0.35  # или 0.40
```

### Проблема: Слишком мало картинок подбирается

**Решение:**
Уменьшите threshold:
```
CLIP_SIMILARITY_THRESHOLD=0.25  # или 0.20
```

---

## Как включить/выключить CLIP на Railway

### Включить CLIP:
1. Railway Dashboard → ваш проект → Variables
2. Добавить/изменить: `CLIP_ENABLED=true`
3. Перезапустить приложение (Deploy)

### Выключить CLIP:
1. Railway Dashboard → Variables
2. Установить: `CLIP_ENABLED=false`
3. Перезапустить приложение

### Подкрутить threshold без редактирования кода:
1. Railway Dashboard → Variables
2. Изменить: `CLIP_SIMILARITY_THRESHOLD=0.35`
3. Перезапустить приложение

---

## Рекомендации для Production

```bash
# Оптимальные настройки для Railway
CLIP_ENABLED=true
CLIP_SIMILARITY_THRESHOLD=0.30
CLIP_MIN_CANDIDATES=8
CLIP_MAX_CANDIDATES=20

# Перевод отключён (рекомендуется)
TRANSLATION_ENABLED=false
TRANSLATION_PROVIDER=none
```

Эти настройки обеспечивают:
- ✅ Семантический подбор картинок через CLIP
- ✅ Фильтрация нерелевантных изображений
- ✅ Отсутствие ошибок LibreTranslate
- ✅ Предсказуемое качество результатов

---

## Примеры логов: Перевод (новый универсальный слой)

### ✅ Сценарий 1: Перевод отключён (TRANSLATION_ENABLED=false)

```
==================================================
🌐 TRANSLATION CONFIGURATION (Image Search)
==================================================
TRANSLATION_ENABLED: False
TRANSLATION_PROVIDER: none
TRANSLATION_TARGET_LANG: en
⚠️ Translation DISABLED for image search
   → Using original text for all image queries
   → Relying on CLIP semantic matching + multilingual photo stocks
==================================================

🔍 Searching image for slide: 'Анализ рынка'
  🎯 Keywords extracted: ['анализ', 'рынка']

  🌐 Image search language: ru
  ⚠️ Translation disabled (TRANSLATION_ENABLED=false)
     Using original query: 'анализ рынка'

  🤖 Using CLIP semantic matching for better relevance
  📊 Found 15 candidates, applying CLIP ranking...
  ✅ CLIP selected: https://... (similarity=0.756, source=Pexels)
```

### ✅ Сценарий 2: Перевод включён, провайдер 'none'

```
==================================================
🌐 TRANSLATION CONFIGURATION (Image Search)
==================================================
TRANSLATION_ENABLED: True
TRANSLATION_PROVIDER: none
TRANSLATION_TARGET_LANG: en
ℹ️ Translation enabled but provider set to 'none'
   → No actual translation will occur
   → Using original text (same as TRANSLATION_ENABLED=false)
==================================================

🔍 Searching image for slide: 'Рост доходов'

  🌐 Image search language: ru
  🌐 Translation: ENABLED, provider=none, target=en
  ℹ️ Provider set to 'none' - no translation
     Using original: 'рост доходов'
```

### ✅ Сценарий 3: LibreTranslate включён (TRANSLATION_PROVIDER=libre)

```
==================================================
🌐 TRANSLATION CONFIGURATION (Image Search)
==================================================
TRANSLATION_ENABLED: True
TRANSLATION_PROVIDER: libre
TRANSLATION_TARGET_LANG: en
✅ Translation provider: LibreTranslate
   → LibreTranslate URL: http://localhost:5001
   → Target language: en
   → Note: Ensure LibreTranslate service is running
==================================================

🔍 Searching image for slide: 'Стратегия роста'

  🌐 Image search language: ru
  🌐 Translation: ENABLED, provider=libre, target=en
  🌐 LibreTranslate: 'стратегия роста' → en at http://localhost:5001
  ✅ LibreTranslate: 'стратегия роста' → 'growth strategy'

  🤖 Using CLIP semantic matching...
  ✅ CLIP selected: https://... (similarity=0.812, source=Pexels)
```

### ⚠️ Сценарий 4: LibreTranslate недоступен (connection error)

```
🔍 Searching image for slide: 'Продажи'

  🌐 Image search language: ru
  🌐 Translation: ENABLED, provider=libre, target=en
  🌐 LibreTranslate: 'продажи' → en at http://localhost:5001
  ⚠️ LibreTranslate connection error (service unavailable)
     Error: [Errno 111] Connection refused
     Using original text

  🤖 Using CLIP semantic matching...
  (продолжает работу с оригинальным текстом)
```

### ✅ Сценарий 5: Внешний API (TRANSLATION_PROVIDER=external)

```
==================================================
🌐 TRANSLATION CONFIGURATION (Image Search)
==================================================
TRANSLATION_ENABLED: True
TRANSLATION_PROVIDER: external
TRANSLATION_TARGET_LANG: en
✅ Translation provider: External API
   → External URL: https://translation.googleapis.com/v2/translate
   → Target language: en
   → Timeout: 5.0s
==================================================

🔍 Searching image for slide: 'Цифровая трансформация'

  🌐 Image search language: ru
  🌐 Translation: ENABLED, provider=external, target=en
  🌐 External translation: 'цифровая трансформация' → en
  ✅ External translation: 'цифровая трансфор...' → 'digital transformation'
```

### ℹ️ Сценарий 6: Текст уже на английском (skip translation)

```
🔍 Searching image for slide: 'Market Analysis'

  🌐 Image search language: en
  ℹ️ Text already in target language (en)
     Skipping translation: 'Market Analysis'

  🤖 Using CLIP semantic matching...
```
