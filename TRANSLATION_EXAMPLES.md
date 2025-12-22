# Примеры использования Translation Layer

## 1. Базовое использование

### Перевод запроса для поиска изображений

```python
from app import translate_for_image_search

# Простой перевод (auto-detect языка)
translated = translate_for_image_search("анализ рынка")
# Результат зависит от конфигурации:
# - TRANSLATION_ENABLED=false → "анализ рынка" (оригинал)
# - TRANSLATION_PROVIDER=libre → "market analysis" (переведено)

# С явным указанием языка источника
translated = translate_for_image_search(
    "стратегия роста", 
    source_lang='ru',
    context="business presentation"
)

# Английский текст (пропустит перевод)
translated = translate_for_image_search("growth strategy")
# → "growth strategy" (unchanged, already English)
```

---

## 2. Интеграция в существующий код

### Замена старой функции translate_keyword_to_english

**Было:**
```python
translated = translate_keyword_to_english(keyword, topic)
```

**Стало (новый API):**
```python
translated = translate_for_image_search(
    keyword, 
    context=topic
)
```

**Обратная совместимость:**
Старая функция `translate_keyword_to_english()` всё ещё работает и автоматически использует новый слой:

```python
# Это работает без изменений!
translated = translate_keyword_to_english("продажи", topic="бизнес")
```

---

## 3. Адаптация external_translate под конкретный API

### Google Translate API

```python
# В app.py, функция external_translate() (строки ~1025-1095)

def external_translate(text: str, target_lang: str = 'en', source_lang: str = None) -> str:
    if not EXTERNAL_TRANSLATE_URL:
        return text
    
    try:
        # Google Translate API v2
        headers = {
            'Content-Type': 'application/json',
        }
        
        payload = {
            'q': text,
            'target': target_lang,
            'format': 'text',
            'key': EXTERNAL_TRANSLATE_API_KEY  # API key в параметрах, не в headers
        }
        
        if source_lang:
            payload['source'] = source_lang
        
        response = requests.post(
            EXTERNAL_TRANSLATE_URL,  # https://translation.googleapis.com/language/translate/v2
            json=payload,
            headers=headers,
            timeout=EXTERNAL_TRANSLATE_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            # Google API структура: data.translations[0].translatedText
            translated = data.get('data', {}).get('translations', [{}])[0].get('translatedText', '')
            return translated.strip() if translated else text
        else:
            print(f"  ⚠️ Google Translate error {response.status_code}")
            return text
            
    except Exception as e:
        print(f"  ⚠️ Translation exception: {e}")
        return text
```

### DeepL API

```python
def external_translate(text: str, target_lang: str = 'en', source_lang: str = None) -> str:
    if not EXTERNAL_TRANSLATE_URL:
        return text
    
    try:
        # DeepL API
        headers = {
            'Authorization': f'DeepL-Auth-Key {EXTERNAL_TRANSLATE_API_KEY}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'text': [text],  # DeepL принимает массив
            'target_lang': target_lang.upper(),  # DeepL требует uppercase ('EN', 'RU')
        }
        
        if source_lang:
            payload['source_lang'] = source_lang.upper()
        
        response = requests.post(
            EXTERNAL_TRANSLATE_URL,  # https://api.deepl.com/v2/translate
            json=payload,
            headers=headers,
            timeout=EXTERNAL_TRANSLATE_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            # DeepL структура: translations[0].text
            translated = data.get('translations', [{}])[0].get('text', '')
            return translated.strip() if translated else text
        else:
            print(f"  ⚠️ DeepL error {response.status_code}")
            return text
            
    except Exception as e:
        print(f"  ⚠️ Translation exception: {e}")
        return text
```

### Azure Translator

```python
def external_translate(text: str, target_lang: str = 'en', source_lang: str = None) -> str:
    if not EXTERNAL_TRANSLATE_URL:
        return text
    
    try:
        # Azure Translator
        headers = {
            'Ocp-Apim-Subscription-Key': EXTERNAL_TRANSLATE_API_KEY,
            'Ocp-Apim-Subscription-Region': os.getenv('AZURE_REGION', 'global'),
            'Content-Type': 'application/json',
        }
        
        params = {
            'api-version': '3.0',
            'to': target_lang
        }
        
        if source_lang:
            params['from'] = source_lang
        
        body = [{'text': text}]
        
        response = requests.post(
            EXTERNAL_TRANSLATE_URL,  # https://api.cognitive.microsofttranslator.com/translate
            params=params,
            headers=headers,
            json=body,
            timeout=EXTERNAL_TRANSLATE_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            # Azure структура: [0].translations[0].text
            translated = data[0].get('translations', [{}])[0].get('text', '')
            return translated.strip() if translated else text
        else:
            print(f"  ⚠️ Azure Translator error {response.status_code}")
            return text
            
    except Exception as e:
        print(f"  ⚠️ Translation exception: {e}")
        return text
```

---

## 4. Проверка доступности сервисов

### Проверка LibreTranslate

```python
from app import is_libretranslate_available

if is_libretranslate_available():
    print("✅ LibreTranslate is running")
else:
    print("❌ LibreTranslate unavailable")
```

### Проверка конфигурации при старте

```python
# Этот код выполняется автоматически при запуске app.py
# Показывает статус всех переводчиков

from app import (
    TRANSLATION_ENABLED, 
    TRANSLATION_PROVIDER, 
    TRANSLATION_TARGET_LANG,
    LIBRETRANSLATE_URL,
    EXTERNAL_TRANSLATE_URL
)

print(f"Translation enabled: {TRANSLATION_ENABLED}")
print(f"Provider: {TRANSLATION_PROVIDER}")
print(f"Target language: {TRANSLATION_TARGET_LANG}")

if TRANSLATION_PROVIDER == 'libre':
    print(f"LibreTranslate URL: {LIBRETRANSLATE_URL}")
elif TRANSLATION_PROVIDER == 'external':
    print(f"External URL: {EXTERNAL_TRANSLATE_URL}")
```

---

## 5. Кеширование переводов

### Автоматическое кеширование

Переводы автоматически кешируются в памяти:

```python
# Первый вызов - выполняет HTTP запрос
result1 = translate_for_image_search("стратегия роста", context="business")
# → HTTP call to translation service
# → "growth strategy"

# Второй вызов с теми же параметрами - из кеша
result2 = translate_for_image_search("стратегия роста", context="business")
# → Cached result
# → "growth strategy"
```

### Очистка кеша

```python
from app import TRANSLATION_CACHE

# Просмотр кеша
print(f"Cached translations: {len(TRANSLATION_CACHE)}")

# Очистка кеша
TRANSLATION_CACHE.clear()
```

---

## 6. Конфигурация через environment variables

### Пример .env для разных сценариев

**Development (без перевода):**
```bash
TRANSLATION_ENABLED=false
TRANSLATION_PROVIDER=none
```

**Development (с локальным LibreTranslate):**
```bash
TRANSLATION_ENABLED=true
TRANSLATION_PROVIDER=libre
LIBRETRANSLATE_URL=http://localhost:5001
LIBRETRANSLATE_TIMEOUT=10
```

**Production (с Google Translate):**
```bash
TRANSLATION_ENABLED=true
TRANSLATION_PROVIDER=external
TRANSLATION_TARGET_LANG=en
EXTERNAL_TRANSLATE_URL=https://translation.googleapis.com/language/translate/v2
EXTERNAL_TRANSLATE_API_KEY=your-google-api-key-here
EXTERNAL_TRANSLATE_TIMEOUT=5.0
```

**Production (с DeepL):**
```bash
TRANSLATION_ENABLED=true
TRANSLATION_PROVIDER=external
TRANSLATION_TARGET_LANG=en
EXTERNAL_TRANSLATE_URL=https://api.deepl.com/v2/translate
EXTERNAL_TRANSLATE_API_KEY=your-deepl-api-key-here
EXTERNAL_TRANSLATE_TIMEOUT=5.0
```

---

## 7. Unit Testing

### Тестирование с mock провайдером

```python
import os
import unittest
from unittest.mock import patch
from app import translate_for_image_search

class TestTranslation(unittest.TestCase):
    
    @patch.dict(os.environ, {
        'TRANSLATION_ENABLED': 'false',
        'TRANSLATION_PROVIDER': 'none'
    })
    def test_translation_disabled(self):
        """When disabled, should return original text"""
        result = translate_for_image_search("анализ рынка")
        self.assertEqual(result, "анализ рынка")
    
    @patch.dict(os.environ, {
        'TRANSLATION_ENABLED': 'true',
        'TRANSLATION_PROVIDER': 'none'
    })
    def test_provider_none(self):
        """Provider 'none' should return original text"""
        result = translate_for_image_search("стратегия роста")
        self.assertEqual(result, "стратегия роста")
    
    def test_english_text_skip(self):
        """English text should skip translation"""
        result = translate_for_image_search("market analysis")
        self.assertEqual(result, "market analysis")
    
    @patch('app.libre_translate')
    @patch.dict(os.environ, {
        'TRANSLATION_ENABLED': 'true',
        'TRANSLATION_PROVIDER': 'libre'
    })
    def test_libre_provider(self, mock_libre):
        """Should call libre_translate when provider is 'libre'"""
        mock_libre.return_value = "market analysis"
        result = translate_for_image_search("анализ рынка")
        mock_libre.assert_called_once()
        self.assertEqual(result, "market analysis")
```

---

## 8. Логирование и отладка

### Включение подробных логов

Логи автоматически выводятся при каждом вызове:

```python
translate_for_image_search("анализ рынка", context="business")

# Вывод в консоль:
# 🌐 Image search language: ru (context: business)
# ⚠️ Translation disabled (TRANSLATION_ENABLED=false)
#    Using original query: 'анализ рынка'
```

### Добавление собственных логов

```python
def translate_for_image_search(text: str, source_lang: str = None, context: str = '') -> str:
    
    # Добавьте свой лог
    if DEBUG:
        print(f"[DEBUG] Translation input: {text}")
        print(f"[DEBUG] Provider: {TRANSLATION_PROVIDER}")
        print(f"[DEBUG] Result: {translated}")
    
    return translated
```

---

## 9. Error Handling

### Graceful Degradation

Все функции перевода реализуют graceful degradation:

```python
try:
    translated = translate_for_image_search("стратегия роста")
    # Всегда вернёт строку (либо переведённую, либо оригинальную)
    # Никогда не вызовет exception в основной код
except Exception:
    # Этот блок никогда не выполнится
    pass
```

### Fallback chain

```
1. Try translation
   ↓ (error)
2. Return original text
   ↓ (always succeeds)
3. Continue image search with original query
```

---

## 10. Best Practices

### ✅ DO

```python
# Использовать новый API для всех новых вызовов
translated = translate_for_image_search(query, context=topic)

# Указывать context для лучшего кеширования
translated = translate_for_image_search(
    query, 
    context=f"{topic}:{slide_title}"
)

# Проверять конфигурацию перед использованием опциональных фич
if TRANSLATION_ENABLED and TRANSLATION_PROVIDER == 'external':
    # Use external API features
    pass
```

### ❌ DON'T

```python
# Не делать несколько запросов подряд без context
translate_for_image_search("рынок")
translate_for_image_search("рынок")  # Кеш не сработает

# Лучше:
translate_for_image_search("рынок", context="business")
translate_for_image_search("рынок", context="business")  # Кеш сработает

# Не обрабатывать exceptions вручную (уже есть внутри)
try:
    translated = translate_for_image_search(query)
except:  # Unnecessary!
    translated = query
```

---

## Заключение

Новый универсальный слой перевода предоставляет:

- 🔄 Гибкость выбора провайдера через `.env`
- 🛡️ Graceful degradation при любых ошибках
- ⚡ Кеширование для повышения производительности
- 🌍 Поддержка мультиязычности без жёсткой привязки к одному сервису
- 🔧 Простая адаптация под любой внешний API

Для подробной информации см.:
- [TRANSLATION_GUIDE.md](./TRANSLATION_GUIDE.md) - Полное руководство
- [RAILWAY_CONFIG.md](./RAILWAY_CONFIG.md) - Настройка для Railway
- [app.py](./app.py) - Исходный код (строки 965-1195)
