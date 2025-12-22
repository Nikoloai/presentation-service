# Translation Layer - Руководство по настройке

## Обзор

SlideRush теперь использует **универсальный слой перевода** для поиска изображений, который позволяет:

- ✅ Полностью отключить перевод (рекомендуется с CLIP)
- ✅ Использовать локальный LibreTranslate
- ✅ Использовать внешний облачный API (Google Translate, DeepL и т.д.)
- ✅ Гибко переключаться между провайдерами через `.env`
- ✅ Сохранять мультиязычность платформы без зависимости от "битых" сервисов

---

## Быстрый старт

### Сценарий 1: Отключить перевод (рекомендуется)

**Когда использовать:**
- У вас включен CLIP (он понимает семантику на любом языке)
- Нет доступа к LibreTranslate или внешнему API
- Хотите максимально упростить конфигурацию

**Настройка `.env`:**
```bash
TRANSLATION_ENABLED=false
TRANSLATION_PROVIDER=none
```

**Результат:**
- Все запросы к фотостокам идут на оригинальном языке (русский/английский)
- CLIP делает семантический подбор независимо от языка запроса
- Никаких ошибок Connection refused
- Быстрая генерация без задержек на перевод

---

### Сценарий 2: Использовать LibreTranslate (локально)

**Когда использовать:**
- У вас запущен локальный LibreTranslate сервер
- Хотите переводить запросы в английский для лучшей индексации Pexels/Unsplash

**Настройка `.env`:**
```bash
TRANSLATION_ENABLED=true
TRANSLATION_PROVIDER=libre
TRANSLATION_TARGET_LANG=en
LIBRETRANSLATE_URL=http://localhost:5001
LIBRETRANSLATE_TIMEOUT=10
```

**Требования:**
1. Установить LibreTranslate:
   ```bash
   pip install libretranslate
   ```

2. Запустить сервер:
   ```bash
   libretranslate --host 0.0.0.0 --port 5001
   ```

**Результат:**
- Русские запросы переводятся в английский
- Английские запросы пропускаются (already in target language)
- При ошибке LibreTranslate → fallback на оригинальный текст

---

### Сценарий 3: Использовать внешний API (Google Translate, DeepL)

**Когда использовать:**
- Работаете на production без локального LibreTranslate
- Нужен стабильный облачный переводчик
- Готовы использовать платный API

**Настройка `.env`:**
```bash
TRANSLATION_ENABLED=true
TRANSLATION_PROVIDER=external
TRANSLATION_TARGET_LANG=en
EXTERNAL_TRANSLATE_URL=https://translation.googleapis.com/v2/translate
EXTERNAL_TRANSLATE_API_KEY=your-google-api-key-here
EXTERNAL_TRANSLATE_TIMEOUT=5.0
```

**Адаптация под конкретный API:**

Файл: `app.py`, функция `external_translate()` (строки 1025-1095)

Для Google Translate API:
```python
headers = {
    'Authorization': f'Bearer {EXTERNAL_TRANSLATE_API_KEY}'
}
payload = {
    'q': text,
    'target': target_lang,
    'format': 'text'
}
```

Для DeepL API:
```python
headers = {
    'Authorization': f'DeepL-Auth-Key {EXTERNAL_TRANSLATE_API_KEY}'
}
payload = {
    'text': [text],
    'target_lang': target_lang.upper()
}
```

---

## Переменные окружения

### Основные параметры

| Переменная | Значения | По умолчанию | Описание |
|-----------|----------|--------------|----------|
| `TRANSLATION_ENABLED` | `true`, `false` | `false` | Включить/выключить перевод |
| `TRANSLATION_PROVIDER` | `none`, `libre`, `external` | `none` | Выбор провайдера |
| `TRANSLATION_TARGET_LANG` | `en`, `ru`, etc. | `en` | Целевой язык |

### LibreTranslate (TRANSLATION_PROVIDER=libre)

| Переменная | Пример | Описание |
|-----------|---------|----------|
| `LIBRETRANSLATE_URL` | `http://localhost:5001` | URL сервера LibreTranslate |
| `LIBRETRANSLATE_TIMEOUT` | `10` | Timeout в секундах |

### External API (TRANSLATION_PROVIDER=external)

| Переменная | Пример | Описание |
|-----------|---------|----------|
| `EXTERNAL_TRANSLATE_URL` | `https://api.deepl.com/v2/translate` | URL внешнего API |
| `EXTERNAL_TRANSLATE_API_KEY` | `your-api-key` | API ключ |
| `EXTERNAL_TRANSLATE_TIMEOUT` | `5.0` | Timeout в секундах |

---

## Логика работы

### Блок-схема

```
┌─────────────────────────────────┐
│ translate_for_image_search()    │
│ (универсальная точка входа)     │
└────────────┬────────────────────┘
             │
             ▼
    ┌────────────────────┐
    │ TRANSLATION_ENABLED │
    │    == false?        │
    └────┬────────────────┘
         │ YES → return original text
         │
         ▼ NO
    ┌────────────────────────┐
    │ Text already in        │
    │ target language?       │
    └────┬───────────────────┘
         │ YES → return text
         │
         ▼ NO
    ┌────────────────────────┐
    │ Check cache            │
    └────┬───────────────────┘
         │ Found → return cached
         │
         ▼ Not found
    ┌────────────────────────┐
    │ TRANSLATION_PROVIDER   │
    └────┬───────────────────┘
         │
         ├─ 'none' ─────────► return original text
         │
         ├─ 'libre' ────────► libre_translate()
         │                     └─► LibreTranslate HTTP call
         │                         └─► On error: fallback to original
         │
         └─ 'external' ─────► external_translate()
                               └─► External API HTTP call
                                   └─► On error: fallback to original
```

---

## Мультиязычность платформы

**Важно:** Платформа остаётся **полностью мультиязычной**:

### Что НЕ затрагивает этот слой перевода:

✅ **Язык интерфейса** - пользователь выбирает в UI (русский/английский)  
✅ **Язык слайдов** - задаётся пользователем при создании презентации  
✅ **Генерация текста** - OpenAI генерирует на языке пользователя  

### Что затрагивает:

⚙️ **Только поиск картинок** - переводятся запросы к Pexels/Unsplash (опционально)

### Рекомендация:

При использовании **CLIP** перевод **не нужен**, т.к.:
- CLIP понимает семантику текста независимо от языка
- Современные фотостоки индексируют картинки мультиязычно
- Исключаются ошибки и задержки перевода

---

## Примеры логов

### Отключен перевод (рекомендуется)

```
🌐 TRANSLATION CONFIGURATION (Image Search)
TRANSLATION_ENABLED: False
TRANSLATION_PROVIDER: none
⚠️ Translation DISABLED for image search
   → Using original text for all image queries
   → Relying on CLIP semantic matching + multilingual photo stocks

🔍 Searching image for slide: 'Анализ рынка'
  🌐 Image search language: ru
  ⚠️ Translation disabled (TRANSLATION_ENABLED=false)
     Using original query: 'анализ рынка'
  🤖 Using CLIP semantic matching...
  ✅ CLIP selected: https://... (similarity=0.812)
```

### LibreTranslate включен

```
🌐 TRANSLATION CONFIGURATION (Image Search)
TRANSLATION_ENABLED: True
TRANSLATION_PROVIDER: libre
✅ Translation provider: LibreTranslate
   → LibreTranslate URL: http://localhost:5001

🔍 Searching image for slide: 'Стратегия роста'
  🌐 Image search language: ru
  🌐 LibreTranslate: 'стратегия роста' → en
  ✅ LibreTranslate: 'стратегия роста' → 'growth strategy'
  🤖 Using CLIP semantic matching...
  ✅ CLIP selected: https://... (similarity=0.856)
```

### External API включен

```
🌐 TRANSLATION CONFIGURATION (Image Search)
TRANSLATION_ENABLED: True
TRANSLATION_PROVIDER: external
✅ Translation provider: External API
   → External URL: https://api.deepl.com/v2/translate

🔍 Searching image for slide: 'Цифровая трансформация'
  🌐 External translation: 'цифровая трансформация' → en
  ✅ External translation: 'цифровая трансформ...' → 'digital transformation'
```

---

## FAQ

### Q: Нужно ли переводить запросы для CLIP?

**A:** Нет. CLIP понимает семантику текста на любом языке (русский, английский, и др.). Перевод нужен только если вы **не используете CLIP** и хотите улучшить результаты keyword search.

### Q: Что делать если LibreTranslate даёт ошибки Connection refused?

**A:** Установите в `.env`:
```bash
TRANSLATION_ENABLED=false
TRANSLATION_PROVIDER=none
```

### Q: Как быстро переключиться с LibreTranslate на внешний API?

**A:** Измените только одну переменную:
```bash
TRANSLATION_PROVIDER=external  # было: libre
```

### Q: Можно ли использовать несколько провайдеров одновременно?

**A:** Нет, но можно легко переключаться через `.env` без изменения кода.

### Q: Какой провайдер рекомендуется для production?

**A:** 
1. **С CLIP:** `TRANSLATION_PROVIDER=none` (оптимально)
2. **Без CLIP:** `TRANSLATION_PROVIDER=external` (если есть бюджет на API) или `TRANSLATION_PROVIDER=libre` (если есть стабильный LibreTranslate сервер)

---

## Миграция со старой схемы

Если у вас была старая конфигурация:

**Было:**
```bash
TRANSLATION_ENABLED=true
LIBRETRANSLATE_URL=http://localhost:5001
```

**Стало:**
```bash
TRANSLATION_ENABLED=true
TRANSLATION_PROVIDER=libre  # новый параметр
TRANSLATION_TARGET_LANG=en  # новый параметр
LIBRETRANSLATE_URL=http://localhost:5001  # без изменений
```

**Обратная совместимость:** Старый код `translate_keyword_to_english()` всё ещё работает, но внутри использует новый универсальный слой `translate_for_image_search()`.

---

## Troubleshooting

### Ошибка: "Unknown provider 'libre'"

**Причина:** Опечатка в названии провайдера  
**Решение:** Проверьте `.env`, допустимые значения: `none`, `libre`, `external`

### Ошибка: "EXTERNAL_TRANSLATE_URL not configured"

**Причина:** Установлен `TRANSLATION_PROVIDER=external`, но не указан URL  
**Решение:** Добавьте в `.env`:
```bash
EXTERNAL_TRANSLATE_URL=https://...
EXTERNAL_TRANSLATE_API_KEY=...
```

### Запросы не переводятся, хотя TRANSLATION_ENABLED=true

**Причина:** Вероятно, установлен `TRANSLATION_PROVIDER=none`  
**Решение:** Измените на `libre` или `external`

---

## Ссылки

- [Railway Config Guide](./RAILWAY_CONFIG.md) - Настройка для Railway
- [Upgrade Guide](./UPGRADE_GUIDE.md) - Детали изменений кода
- [LibreTranslate Documentation](https://github.com/LibreTranslate/LibreTranslate)
- [Google Translate API](https://cloud.google.com/translate/docs)
- [DeepL API](https://www.deepl.com/pro-api)
