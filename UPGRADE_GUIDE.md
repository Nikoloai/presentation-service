# Обновление CLIP для Production (Railway)

## 📋 Краткая инструкция

### 1. Изменённые файлы

**Основные изменения:**
- ✅ `app.py` - добавлена конфигурация CLIP из env, улучшенные логи, отключение LibreTranslate
- ✅ `services/image_matcher.py` - добавлен вывод similarity score и топ-3 кандидатов
- ✅ `.env.example` - документация новых параметров
- ✅ `RAILWAY_CONFIG.md` - инструкция для Railway

### 2. Что добавилось

#### Переменные окружения (обязательны для Railway):

```bash
# CLIP конфигурация
CLIP_ENABLED=true                      # Включить/выключить CLIP
CLIP_SIMILARITY_THRESHOLD=0.30         # Порог схожести (0.25-0.40)
CLIP_MIN_CANDIDATES=8                  # Минимум кандидатов
CLIP_MAX_CANDIDATES=20                 # Максимум кандидатов

# Перевод (рекомендуется выключить)
TRANSLATION_ENABLED=false              # Отключить LibreTranslate
```

### 3. Логика работы

#### При старте приложения:

1. **Читает `CLIP_ENABLED` из окружения**
   - Если `true` → пытается инициализировать CLIP
   - Если `false` → использует только keyword search

2. **Выводит подробные логи:**
   ```
   🤖 CLIP CONFIGURATION
   CLIP_ENABLED (from env): True
   CLIP_SIMILARITY_THRESHOLD: 0.30
   ...
   ✅ CLIP initialized successfully
   🎯 Final CLIP status: ACTIVE
   ```

3. **Проверяет LibreTranslate:**
   ```
   🌐 TRANSLATION CONFIGURATION
   TRANSLATION_ENABLED (from env): False
   ⚠️ Translation disabled - using original text
   ```

#### При поиске картинки для слайда:

1. **Если CLIP активен:**
   - Запрашивает 8-20 кандидатов (настраиваемо)
   - Проверяет минимум кандидатов
   - Ранжирует через CLIP
   - Выводит топ-3 с similarity scores
   - Фильтрует по threshold
   - Логирует результат

2. **Если CLIP недоступен:**
   - Логирует причину
   - Fallback на keyword search

3. **Если threshold не пройден:**
   - Логирует `❌ CLIP skipped (best similarity < 0.30)`
   - Пропускает картинку (лучше пусто, чем нерелевантно)

### 4. Примеры логов

#### ✅ Успешный подбор с CLIP:

```
🔍 Searching image for slide: 'Revenue Growth'
  🎯 Keywords extracted: ['revenue', 'growth']
  🤖 Using CLIP semantic matching
     Threshold: 0.30, Min candidates: 8
  📊 Found 15 candidates, applying CLIP ranking...
  📝 CLIP context: 'Revenue Growth. Our Q4...'

  🏆 Top 3 candidates:
     [1] Business chart showing revenue     → 0.782 (Pexels)
     [2] Team meeting presentation         → 0.543 (Unsplash)
     [3] Office interior modern            → 0.234 (Pexels)

  ✅ Best match: 'Business chart...' (similarity: 0.782)
  ✅ CLIP selected: https://... (similarity=0.782, source=Pexels)
```

#### ❌ Пропуск из-за низкого similarity:

```
🔍 Searching image for slide: 'Основные концепции'
  🤖 Using CLIP semantic matching
  📊 Found 12 candidates...

  🏆 Top 3 candidates:
     [1] Abstract pattern geometric        → 0.234 (Pexels)
     [2] Office desk laptop               → 0.198 (Unsplash)
     [3] Mountain landscape                → 0.156 (Pexels)

  ❌ Best match (0.234) below threshold (0.30)
  ❌ CLIP skipped (best similarity < 0.30 threshold)
  🔍 Falling back to traditional keyword search
```

#### ℹ️ CLIP отключён:

```
🔍 Searching image for slide: 'Market Analysis'
  ℹ️ CLIP disabled (CLIP_ENABLED=false)
     Using keyword search only
  🔍 Falling back to traditional keyword search
  ✅ Found unique image: https://...
```

---

## 🚀 Деплой на Railway

### Шаг 1: Установить переменные окружения

В Railway Dashboard → Variables добавить:

```bash
CLIP_ENABLED=true
CLIP_SIMILARITY_THRESHOLD=0.30
CLIP_MIN_CANDIDATES=8
CLIP_MAX_CANDIDATES=20
TRANSLATION_ENABLED=false
```

### Шаг 2: Задеплоить

Railway автоматически пересоберёт приложение при push.

### Шаг 3: Проверить логи

В Railway Logs должны появиться:

```
🤖 CLIP CONFIGURATION
CLIP_ENABLED (from env): True
...
✅ CLIP initialized successfully
🎯 Final CLIP status: ACTIVE
```

Если видите `❌ CLIP initialization failed`:
- Проверьте установку зависимостей в логах
- Временно отключите: `CLIP_ENABLED=false`

---

## ⚙️ Настройка качества

### Много "случайных" картинок?
**Увеличьте threshold:**
```bash
CLIP_SIMILARITY_THRESHOLD=0.35  # или 0.40
```

### Слишком мало картинок?
**Уменьшите threshold:**
```bash
CLIP_SIMILARITY_THRESHOLD=0.25  # или 0.20
```

### Хотите больше вариантов для CLIP?
**Увеличьте max candidates:**
```bash
CLIP_MAX_CANDIDATES=30
```

---

## 🔧 Troubleshooting

### LibreTranslate ошибки на проде

**Симптом:**
```
⚠ LibreTranslate connection error: Connection refused
```

**Решение:**
```bash
TRANSLATION_ENABLED=false
```

### CLIP не работает

**Проверьте логи при старте:**
- Если `❌ CLIP initialization failed` → проблема с зависимостями
- Если `⚠️ CLIP disabled via CLIP_ENABLED=false` → включите через env
- Если `ℹ️ CLIP unavailable` → проверьте `requirements.txt`

### Медленная генерация

**CLIP добавляет 1-2 секунды на слайд.**

Если критично:
```bash
CLIP_MAX_CANDIDATES=10  # меньше кандидатов = быстрее
```

Или отключите:
```bash
CLIP_ENABLED=false
```

---

## 📊 Что изменилось в коде

### app.py

1. **Добавлены параметры из env** (строки 48-87):
   - `CLIP_ENABLED`, `CLIP_SIMILARITY_THRESHOLD`
   - `CLIP_MIN_CANDIDATES`, `CLIP_MAX_CANDIDATES`
   - `TRANSLATION_ENABLED`

2. **Инициализация CLIP при старте** (строки 62-87):
   - Проверка доступности
   - Вывод информации о модели
   - Установка `CLIP_AVAILABLE` flag

3. **Обновлена функция `translate_keyword_to_english`** (строки 929-998):
   - Проверка `TRANSLATION_ENABLED`
   - Логирование когда перевод выключен
   - Лучшая обработка ошибок подключения

4. **Улучшена `search_image_for_slide`** (строки 2276-2357):
   - Использует `CLIP_AVAILABLE` вместо функции
   - Проверка минимума кандидатов
   - Вывод контекста и топ-3 кандидатов
   - Логирование similarity score
   - Подробные сообщения при пропуске

### services/image_matcher.py

1. **Вывод топ-3 кандидатов** (строки 141-146):
   - Показывает лучшие варианты с scores
   - Упрощает отладку

2. **Возврат similarity score** (строки 157-161):
   - Добавляет `_clip_similarity` в результат
   - Используется для логирования

---

## ✅ Checklist после деплоя

- [ ] Переменные окружения добавлены в Railway
- [ ] В логах видно `🎯 Final CLIP status: ACTIVE`
- [ ] Нет ошибок `LibreTranslate connection refused`
- [ ] При генерации презентации видны логи CLIP
- [ ] Качество картинок улучшилось
- [ ] Threshold настроен под ваши нужды

---

**Вопросы?** См. [RAILWAY_CONFIG.md](RAILWAY_CONFIG.md) для деталей.
