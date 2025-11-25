import os
import json
import requests
import re
import hashlib
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
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
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')  # Needed for Flask-Login

# ============================================================================
# Firebase Admin SDK Initialization
# ============================================================================
# This section initializes Firebase Admin SDK for server-side authentication
# The SDK requires a service account key JSON file for secure communication
# with Firebase services

try:
    # Step 1: Get service account key path from environment or use default
    firebase_cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY', 'serviceAccountKey.json')
    print(f"🔍 Checking Firebase service account key at: {firebase_cred_path}")
    
    # Step 2: Verify that the service account key file exists
    if not os.path.exists(firebase_cred_path):
        raise FileNotFoundError(f"Service account key not found at: {firebase_cred_path}")
    
    # Step 3: Validate JSON format and required fields
    with open(firebase_cred_path, 'r') as f:
        key_data = json.load(f)
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in key_data]
        
        if missing_fields:
            raise ValueError(f"Service account key missing required fields: {missing_fields}")
        
        if key_data.get('type') != 'service_account':
            raise ValueError(f"Invalid key type: expected 'service_account', got '{key_data.get('type')}'")
        
        print(f"✅ Service account key validated: Project ID = {key_data.get('project_id')}")
    
    # Step 4: Initialize Firebase Admin SDK with credentials
    cred = credentials.Certificate(firebase_cred_path)
    firebase_admin.initialize_app(cred)
    
    print("✅ Firebase Admin SDK initialized successfully")
    print("   → Token verification: ENABLED")
    print("   → User authentication: READY")
    
except FileNotFoundError as e:
    print(f"⚠️ Firebase initialization failed: {e}")
    print("   → Firebase authentication will NOT work")
    print("   → Please add serviceAccountKey.json to project root")
    print("   → Download from: Firebase Console → Project Settings → Service Accounts")
    
except ValueError as e:
    print(f"⚠️ Firebase initialization failed: {e}")
    print("   → Invalid or corrupted service account key")
    print("   → Please download a new key from Firebase Console")
    
except Exception as e:
    print(f"⚠️ Firebase initialization error: {e}")
    print(f"   → Error type: {type(e).__name__}")
    print("   → Firebase authentication may not work correctly")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Please log in to access this page.'

# Simple admin user storage
ADMIN_USERS = {
    'admin': {
        'password_hash': generate_password_hash(os.getenv('ADMIN_PASSWORD', 'admin123')),
        'id': 'admin'
    }
}

class User(UserMixin):
    def __init__(self, user_id, email=None, is_admin_user=False, name=None, picture=None):
        self.id = user_id
        self.email = email
        self.is_admin_user = is_admin_user
        self.name = name or email
        self.picture = picture

    def is_admin(self):
        return self.is_admin_user

# Lookup user by ID from SQLite
def get_user_by_id(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id, email, name, picture, status FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching user by id: {e}")
        return None

@login_manager.user_loader
def load_user(user_id):
    # Admin shortcut
    if user_id in ADMIN_USERS:
        return User(user_id, is_admin_user=True)
    # Regular user
    try:
        int_id = int(user_id)
    except (ValueError, TypeError):
        return None
    user_data = get_user_by_id(int_id)
    if not user_data:
        return None
    return User(
        user_data['id'],
        email=user_data.get('email'),
        is_admin_user=False,
        name=user_data.get('name'),
        picture=user_data.get('picture')
    )

# Helper functions for Firebase user management
def get_or_create_firebase_user(firebase_uid, email, name='', picture=''):
    """
    Get existing user by Firebase UID or create new one
    Returns (user_data, error)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Try to find user by Firebase UID
        cursor.execute('SELECT * FROM users WHERE firebase_uid = ?', (firebase_uid,))
        user = cursor.fetchone()
        
        if user:
            # User exists, return their data
            conn.close()
            return dict(user), None
        
        # Check if user exists by email (migrating from email/password auth)
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if user:
            # Update existing user with Firebase UID
            cursor.execute(
                'UPDATE users SET firebase_uid = ?, name = ?, picture = ? WHERE email = ?',
                (firebase_uid, name, picture, email)
            )
            conn.commit()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            conn.close()
            return dict(user), None
        
        # Create new user
        cursor.execute(
            '''INSERT INTO users (email, firebase_uid, name, picture, status)
               VALUES (?, ?, ?, ?, 'active')''',
            (email, firebase_uid, name, picture)
        )
        conn.commit()
        user_id = cursor.lastrowid
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        return dict(user), None
        
    except Exception as e:
        print(f"Error in get_or_create_firebase_user: {e}")
        return None, str(e)

# Helper functions for email/password authentication
def validate_email(email):
    """
    Validate email format
    Returns (is_valid, error_message)
    """
    if not email or len(email) < 3:
        return False, "Email is too short"
    if '@' not in email or '.' not in email:
        return False, "Invalid email format"
    if len(email) > 255:
        return False, "Email is too long"
    return True, None

def validate_password(password):
    """
    Validate password strength
    Returns (is_valid, error_message)
    """
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters"
    if len(password) > 128:
        return False, "Password is too long"
    return True, None

def create_user(email, password):
    """
    Create new user with email and password
    Returns (user_id, error)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            conn.close()
            return None, "User with this email already exists"
        
        # Create user
        password_hash = generate_password_hash(password)
        cursor.execute(
            '''INSERT INTO users (email, password_hash, status)
               VALUES (?, ?, 'active')''',
            (email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return user_id, None
        
    except Exception as e:
        print(f"Error creating user: {e}")
        return None, "Failed to create user"

def authenticate_user(email, password):
    """
    Authenticate user with email and password
    Returns (user_data, error)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return None, "Invalid email or password"
        
        if not user['password_hash']:
            return None, "Please sign in with Firebase/Google"
        
        if not check_password_hash(user['password_hash'], password):
            return None, "Invalid email or password"
        
        if user['status'] == 'blocked':
            return None, "Your account has been blocked"
        
        return dict(user), None
        
    except Exception as e:
        print(f"Error authenticating user: {e}")
        return None, "Authentication failed"

# Admin helper functions
def get_all_users():
    """
    Get all users from database
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY registration_date DESC')
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []

def update_user_status(user_id, status):
    """
    Update user status (active/blocked)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET status = ? WHERE id = ?', (status, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating user status: {e}")
        return False

def delete_user(user_id):
    """
    Delete user and their presentations
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Delete user's presentations first
        cursor.execute('DELETE FROM presentations WHERE user_id = ?', (user_id,))
        # Delete user
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False

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

# Initialize SQLite database for users
DB_PATH = 'users.db'

def init_db():
    """Initialize the database with users table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            google_id TEXT UNIQUE,
            firebase_uid TEXT UNIQUE,
            name TEXT,
            picture TEXT,
            status TEXT DEFAULT 'active',
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create presentations table to track user activity
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS presentations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT NOT NULL,
            num_slides INTEGER,
            filename TEXT,
            presentation_type TEXT DEFAULT 'business',
            creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Migration: Add firebase_uid column if it doesn't exist
    # Note: SQLite ALTER TABLE does not support adding UNIQUE constraint directly
    # We add the column first, then create a unique index separately
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'firebase_uid' not in columns:
        # Step 1: Add firebase_uid column without UNIQUE constraint
        cursor.execute('ALTER TABLE users ADD COLUMN firebase_uid TEXT')
        print("✅ Migration: Added firebase_uid column to users table")
        
        # Step 2: Create unique index on firebase_uid column
        # This ensures uniqueness while allowing NULL values
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_firebase_uid ON users(firebase_uid)')
        print("✅ Migration: Created unique index on firebase_uid column")
    
    # Migration: Add presentation_type column if it doesn't exist
    cursor.execute("PRAGMA table_info(presentations)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'presentation_type' not in columns:
        cursor.execute('ALTER TABLE presentations ADD COLUMN presentation_type TEXT DEFAULT "business"')
        print("✅ Migration: Added presentation_type column to presentations table")
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Presentation types configuration
PRESENTATION_TYPES = {
    'business': {
        'name_ru': 'Бизнес-презентация',
        'name_en': 'Business Presentation',
        'icon': '💼',
        'color': '#667eea',
        'structure': [
            {'title': 'Введение', 'description': 'Представьте компанию и тему'},
            {'title': 'Проблема', 'description': 'Опишите проблему или вызов'},
            {'title': 'Решение', 'description': 'Предложите ваше решение'},
            {'title': 'Результаты', 'description': 'Покажите достижения и метрики'},
            {'title': 'Призыв к действию', 'description': 'Следующие шаги'}
        ],
        'tips': 'Фокус на фактах, данных и конкретных результатах. Используйте графики и диаграммы.'
    },
    'sales': {
        'name_ru': 'Продажи',
        'name_en': 'Sales Pitch',
        'icon': '💰',
        'color': '#27ae60',
        'structure': [
            {'title': 'Hook', 'description': 'Привлеките внимание с первых секунд'},
            {'title': 'Проблема', 'description': 'Болевые точки клиента'},
            {'title': 'Решение', 'description': 'Ваш продукт/услуга'},
            {'title': 'Преимущества', 'description': 'Уникальные особенности'},
            {'title': 'Цена', 'description': 'Ценовое предложение'},
            {'title': 'Демонстрация', 'description': 'Примеры и кейсы'},
            {'title': 'Призыв к действию', 'description': 'Закрытие сделки'}
        ],
        'tips': 'Эмоциональность + конкретика. Покажите ROI и быстрые победы.'
    },
    'investor': {
        'name_ru': 'Инвестиционный питч',
        'name_en': 'Investor Pitch',
        'icon': '📈',
        'color': '#e67e22',
        'structure': [
            {'title': 'Проблема', 'description': 'Глобальная проблема на рынке'},
            {'title': 'Решение', 'description': 'Инновационное решение'},
            {'title': 'Рынок', 'description': 'Размер и потенциал рынка'},
            {'title': 'Бизнес-модель', 'description': 'Как вы зарабатываете'},
            {'title': 'Команда', 'description': 'Ключевые люди'},
            {'title': 'Финансы', 'description': 'Прогнозы и потребность в капитале'},
            {'title': 'Призыв к действию', 'description': 'Инвестиционное предложение'}
        ],
        'tips': 'Масштабируемость, рост, команда. Фокус на цифрах и потенциале.'
    },
    'educational': {
        'name_ru': 'Образовательная',
        'name_en': 'Educational',
        'icon': '🎓',
        'color': '#3498db',
        'structure': [
            {'title': 'Введение', 'description': 'Цели и обзор темы'},
            {'title': 'Теория', 'description': 'Основные концепции'},
            {'title': 'Примеры', 'description': 'Практические примеры'},
            {'title': 'Практика', 'description': 'Упражнения и задания'},
            {'title': 'Выводы', 'description': 'Ключевые моменты'},
            {'title': 'Вопросы', 'description': 'Q&A и дополнительные материалы'}
        ],
        'tips': 'Ясность, структура, повторение. Используйте визуализацию и примеры.'
    },
    'startup': {
        'name_ru': 'Стартап-питч',
        'name_en': 'Startup Pitch',
        'icon': '🚀',
        'color': '#9b59b6',
        'structure': [
            {'title': 'Проблема', 'description': 'Какую проблему решаете'},
            {'title': 'Решение', 'description': 'Ваш продукт/сервис'},
            {'title': 'Рынок', 'description': 'Размер и возможности'},
            {'title': 'Бизнес-модель', 'description': 'Как зарабатываете'},
            {'title': 'Traction', 'description': 'Первые результаты'},
            {'title': 'Команда', 'description': 'Кто за этим стоит'},
            {'title': 'Ask', 'description': 'Что нужно для роста'}
        ],
        'tips': 'Продукт, тракшн, команда. Покажите momentum и потенциал роста.'
    }
}

# Supported languages
SUPPORTED_LANGUAGES = {
    'ru': 'Russian',
    'en': 'English',
    'es': 'Spanish',
    'zh': 'Chinese',
    'fr': 'French'
}

# AI role prompts per presentation type and language
def get_ai_role_prompt(presentation_type, language):
    """Get AI system role prompt based on presentation type and language"""
    prompts = {
        'business': {
            'ru': "Ты опытный бизнес-консультант. Создай профессиональную бизнес-презентацию на русском языке.",
            'en': "You are an experienced business consultant. Create a professional business presentation in English.",
            'es': "Eres un consultor de negocios experimentado. Crea una presentación empresarial profesional en español.",
            'zh': "你是一位经验丰富的商业顾问。请用中文创建专业的商务演示文稿。",
            'fr': "Vous êtes un consultant en affaires expérimenté. Créez une présentation professionnelle en français."
        },
        'sales': {
            'ru': "Ты эксперт по продажам. Создай мощный sales pitch на русском языке.",
            'en': "You are a sales expert. Create a strong sales pitch in English.",
            'es': "Eres un experto en ventas. Crea un poderoso pitch de ventas en español.",
            'zh': "你是销售专家。请用中文创建有力的销售演示文稿。",
            'fr': "Vous êtes un expert en ventes. Créez un argumentaire de vente puissant en français."
        },
        'investor': {
            'ru': "Ты опытный инвестор-стартапер. Создай инвесторскую презентацию на русском.",
            'en': "You are a seasoned startup investor. Create an investor pitch deck in English.",
            'es': "Eres un inversor experimentado. Crea una presentación para inversores en español.",
            'zh': "你是一名资深投资人。请用中文创建投资者路演文稿。",
            'fr': "Vous êtes un investisseur aguerri. Créez une présentation pour investisseurs en français."
        },
        'educational': {
            'ru': "Ты профессиональный преподаватель. Создай учебную презентацию на русском.",
            'en': "You are a professional educator. Create an educational presentation in English.",
            'es': "Eres un educador profesional. Crea una presentación educativa en español.",
            'zh': "你是专业教师。请用中文创建教育演示文稿。",
            'fr': "Vous êtes un éducateur professionnel. Créez une présentation éducative en français."
        },
        'startup': {
            'ru': "Ты фаундер стартапа. Создай питч для стартапа на русском.",
            'en': "You are a startup founder. Create a startup pitch in English.",
            'es': "Eres fundador de una startup. Crea un pitch de startup en español.",
            'zh': "你是一名创业者。请用中文创建创业演示文稿。",
            'fr': "Vous êtes fondateur d'une startup. Créez un pitch de startup en français."
        }
    }
    # Default to business/en if not found
    return prompts.get(presentation_type, prompts['business']).get(language, prompts['business']['en'])

# System prompts per presentation type
SYSTEM_PROMPTS = {
    'sales': (
        'Ты опытный продажник с 10+ летним стажем в B2B и B2C. Твоя задача — создать убедительную Sales Pitch презентацию, которая продаёт. Используй эти принципы:\n'
        '- Начни с проблемы клиента (боль, которую он испытывает)\n'
        '- Покажи уникальное решение (почему именно твой продукт)\n'
        '- Подчеркни выгоды и преимущества перед конкурентами\n'
        '- Добавь социальные доказательства (кейсы, отзывы, цифры)\n'
        '- Заверши сильным призывом к действию (CTA: купить, попробовать, демо)\n'
        'Используй активный, убеждающий язык. Часто используй слова: "выгода", "сэкономить", "результат", "рост".'
    ),
    'investor': (
        'Ты опытный предприниматель и инвестор, знаешь, как привлекать денег. Создаёшь Investor Pitch для венчурных фондов. Используй эти принципы:\n'
        '- Определи большую проблему на рынке (Problem)\n'
        '- Покажи масштабируемое решение (Solution)\n'
        '- Приведи размер рынка (TAM, SAM, SOM — покажи масштаб)\n'
        '- Объясни бизнес-модель (как зарабатываем, unit-экономика)\n'
        '- Укажи конкурентное преимущество\n'
        '- Опиши команду (опыт, достижения)\n'
        '- Приведи финансовые показатели и прогнозы (выручка, рост, прибыль)\n'
        '- Скажи, сколько денег нужно и на что потратишь\n'
        'Язык: ориентирован на цифры, ROI, масштабируемость, потенциал роста. Впечатляй данными.'
    ),
    'business': (
        'Ты опытный бизнес-консультант. Создаёшь Business Presentation для внутренних встреч и партнёров. Используй эти принципы:\n'
        '- Введение и контекст ситуации\n'
        '- Описание ключевых вызовов/проблем\n'
        '- Наш подход к решению\n'
        '- Результаты и метрики (данные, графики)\n'
        '- Следующие шаги и рекомендации\n'
        'Язык: профессиональный, ориентирован на факты, данные, результаты. Не слишком продающий, но убеждающий.'
    ),
    'educational': (
        'Ты опытный учитель и методист с опытом создания обучающих курсов. Создаёшь Educational презентацию для студентов или сотрудников. Используй эти принципы:\n'
        '- Определи цели обучения (что они научатся)\n'
        '- Объясни теорию пошагово (основные концепции, простым языком)\n'
        '- Приведи практические примеры и аналогии\n'
        '- Предложи упражнения для закрепления\n'
        '- Резюмируй ключевые выводы\n'
        'Язык: простой, доступный, с примерами и визуализациями. Часто: "например", "представьте", "для практики".'
    )
}

# Structure generator per type
def get_slide_structure_by_type(presentation_type: str, num_slides: int):
    seq = []
    t = presentation_type
    n = max(3, min(10, num_slides))
    if t == 'sales':
        seq = ['Title/Hook'] + ['Customer Problem']*2 + ['Solution & Uniqueness']*2 + ['Benefits & Advantages']*2 + ['Social Proof']*2 + ['Pricing/Offer'] + ['Call-to-Action']*2
    elif t == 'investor':
        seq = ['Problem', 'Solution', 'Market Size', 'Business Model']*1 + ['Business Model'] + ['Competitors & Advantages', 'Team'] + ['Financials & Metrics']*2 + ['Use of Funds']*2 + ['The Ask']
    elif t == 'business':
        seq = ['Intro/Title'] + ['Context/Situation']*2 + ['Key Challenges']*2 + ['Our Approach']*2 + ['Results & Metrics']*2 + ['Next Steps']
    elif t == 'startup':
        seq = ['Title/Hook', 'Problem', 'Solution', 'Market Opportunity', 'Business Model', 'Traction', 'Team', 'Roadmap', 'Financials', 'The Ask']
    else:  # educational
        seq = ['Learning Objectives'] + ['Theory']*3 + ['Examples']*4 + ['Exercises']*4 + ['Key Takeaways']*3
    # Trim or expand
    if len(seq) >= n:
        return seq[:n]
    else:
        # Pad last item
        return seq + [seq[-1]]*(n-len(seq))

# Get presentation type info safely
def get_presentation_type_info(presentation_type: str):
    return PRESENTATION_TYPES.get(presentation_type, PRESENTATION_TYPES['business'])

# Check if current user is admin
def is_admin():
    return current_user.is_authenticated and hasattr(current_user, 'is_admin_user') and current_user.is_admin_user


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


def generate_slide_content_in_language(topic, num_slides, language='en', presentation_type='business'):
    """
    Generate slide content using OpenAI ChatGPT API in the specified language
    with structure optimized for presentation type
    """
    try:
        print(f"Generating content in language: {language}, type: {presentation_type}")
        
        # Get presentation type info
        type_info = get_presentation_type_info(presentation_type)
        structure_guide = type_info.get('structure', [])
        tips = type_info.get('tips', '')
        
        # Build structure guidance string from type-specific sequence
        guided_sequence = get_slide_structure_by_type(presentation_type, num_slides)
        structure_text = "\n".join([f"- Slide {i+1}: {title}" for i, title in enumerate(guided_sequence)])
        
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Get AI role prompt based on type and language
        language_name = SUPPORTED_LANGUAGES.get(language, 'English')
        system_prompt = get_ai_role_prompt(presentation_type, language)

        # Create prompt based on language and presentation type
        if language == 'ru':
            type_name_ru = type_info.get('name_ru', 'Презентация')
            prompt = f"""Создай структурированную презентацию на тему: "{topic}"
Количество слайдов: {num_slides}
Тип презентации: {type_name_ru}

РЕКОМЕНДУЕМАЯ СТРУКТУРА ДЛЯ ЭТОГО ТИПА:
{structure_text}

СОВЕТ ПО СТИЛЮ: {tips}

ВАЖНО: Презентация должна состоять из ТЕЗИСОВ, а не описаний!
Используй рекомендованную структуру как ориентир, но адаптируй её под тему "{topic}".

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
        elif language == 'es':
            prompt = f"""Crea una presentación estructurada sobre el tema: "{topic}"
Número de diapositivas: {num_slides}

IMPORTANTE: La presentación debe consistir en DECLARACIONES DE TESIS, no descripciones.

TESIS — una declaración clave que revela parte del tema.
NO solo describas, formula ideas y argumentos específicos.

ESTRUCTURA DE TESIS:
- Diapositiva 1: Idea principal del tema (declaración central)
- Diapositivas 2-{num_slides-1}: Aspectos clave, beneficios, aplicaciones
- Diapositiva {num_slides}: Conclusión, futuro, conclusión

Cada tesis debe:
✓ Ser una declaración específica directamente relacionada con "{topic}"
✓ Contener 2-3 oraciones precisas con DETALLES y EJEMPLOS CONCRETOS
✓ Desarrollar el tema principal
✓ Formar una cadena lógica con otras tesis
✓ EVITAR frases plantilla como "tecnología clave", "era digital", "sociedad moderna"
✓ Usar TERMINOLOGÍA ESPECÍFICA y hechos relevantes solo para "{topic}"

Para cada diapositiva, devuelve JSON con campos:
- "title": Título breve (2-3 palabras) específico para el tema
- "search_keyword": Palabras clave para búsqueda de imágenes en inglés (3-4 palabras)
- "content": TESIS — declaración específica (2-3 oraciones con detalles)

EJEMPLO de tesis correctas para "Perros":
{{
  "slides": [
    {{"title": "Evolución de los Perros", "search_keyword": "dog evolution wolf domestication", "content": "Los perros descienden de lobos aproximadamente hace 15,000 años a través de la domesticación. Las investigaciones genéticas muestran que los primeros perros aparecieron en Asia Oriental y se expandieron mundialmente con los humanos. Las razas modernas son resultado de la cría selectiva en los últimos 200 años."}},
    {{"title": "Razas y Funciones", "search_keyword": "dog breeds working dogs types", "content": "Existen más de 400 razas de perros reconocidas, cada una criada para tareas específicas. Las razas pastoriles (Border Collies, Pastores) manejan rebaños, las de caza (Retrievers, Spaniels) asisten en la caza, mientras que las razas guardianas (Dobermans, Rottweilers) protegen propiedades. Las razas de compañía (Chihuahuas, Terriers) se crían exclusivamente para compañía."}},
    {{"title": "Inteligencia Canina", "search_keyword": "dog intelligence training cognition", "content": "Los perros pueden memorizar hasta 165 palabras y gestos, comparable a las habilidades cognitivas de un niño de dos años. Los Border Collies se consideran la raza más inteligente, comprendiendo nuevos comandos tras solo 5 repeticiones. Las investigaciones muestran que los perros distinguen emociones humanas a través de expresiones faciales y tono de voz."}}
  ]
}}

INCORRECTO (frases plantilla):
"Los perros se están convirtiendo en un factor clave en la sociedad moderna. La adopción de estas tecnologías desbloquea nuevas posibilidades."

CORRECTO (hechos concretos):
"Los perros poseen un sentido del olfato 10,000 veces más agudo que los humanos debido a 300 millones de receptores olfativos. Esto les permite detectar drogas, explosivos e incluso diagnosticar cáncer en etapas tempranas."

Devuelve SOLO JSON válido sin texto adicional.

CRÍTICO: 
- Cada tesis debe contener HECHOS, NÚMEROS, EJEMPLOS relacionados con "{topic}"
- NO uses frases genéricas sobre "tecnología", "innovación", "futuro" sin especificaciones
- El título y contenido de cada diapositiva deben estar LÓGICAMENTE conectados
- Cada search_keyword debe ser DIFERENTE y específico"""
        elif language == 'zh':
            prompt = f"""创建关于主题 "{topic}" 的结构化演示文稿
幻灯片数量: {num_slides}

重要：演示文稿必须由论点陈述组成，而不是描述！

论点 — 揭示主题部分内容的关键陈述。
不要只是描述，要提出具体的想法和论据。

论点结构：
- 幻灯片 1: 主题的主要观点（核心陈述）
- 幻灯片 2-{num_slides-1}: 关键方面、优势、应用
- 幻灯片 {num_slides}: 结论、未来、要点

每个论点必须：
✓ 是与 "{topic}" 直接相关的具体陈述
✓ 包含 2-3 个带有具体细节和示例的精确句子
✓ 发展主要主题
✓ 与其他论点形成逻辑链
✓ 避免使用 "关键技术"、"数字时代"、"现代社会" 等模板短语
✓ 使用仅与 "{topic}" 相关的特定术语和事实

对于每张幻灯片，返回包含以下字段的 JSON：
- "title": 简短标题（2-3 个词），针对主题
- "search_keyword": 英文图像搜索关键词（3-4 个词）
- "content": 论点 — 具体陈述（2-3 个带细节的句子）

"狗" 的正确论点示例：
{{
  "slides": [
    {{"title": "狗的进化", "search_keyword": "dog evolution wolf domestication", "content": "狗大约在 15,000 年前通过驯化从狼进化而来。基因研究表明，第一批狗出现在东亚，并随着人类传播到世界各地。现代品种是过去 200 年选择性繁殖的结果。"}},
    {{"title": "品种和功能", "search_keyword": "dog breeds working dogs types", "content": "有超过 400 种被认可的狗品种，每种都为特定任务而培育。牧羊犬（边境牧羊犬、德国牧羊犬）管理牲畜，猎犬（寻回犬、西班牙猎犬）协助狩猎，而护卫犬（杜宾犬、罗威纳犬）保护财产。玩具犬（吉娃娃、梗犬）专门用于伴侣。"}},
    {{"title": "犬类智力", "search_keyword": "dog intelligence training cognition", "content": "狗能记住多达 165 个单词和手势，相当于两岁儿童的认知能力。边境牧羊犬被认为是最聪明的品种，只需 5 次重复就能理解新命令。研究表明狗能通过面部表情和语调区分人类情感。"}}
  ]
}}

错误（模板短语）：
"狗正在成为现代社会发展的关键因素。采用这些技术开启了新的可能性。"

正确（具体事实）：
"狗的嗅觉比人类敏锐 10,000 倍，因为它们拥有 3 亿个嗅觉受体。这使它们能够检测毒品、爆炸物，甚至在早期诊断癌症。"

仅返回有效的 JSON，不包含额外文本。

关键：
- 每个论点必须包含与 "{topic}" 相关的具体事实、数字、示例
- 不要使用没有具体说明的 "技术"、"创新"、"未来" 等通用短语
- 每张幻灯片的标题和内容必须在逻辑上相关联
- 每个 search_keyword 必须是不同的且具体的"""
        elif language == 'fr':
            prompt = f"""Créez une présentation structurée sur le sujet : "{topic}"
Nombre de diapositives : {num_slides}

IMPORTANT : La présentation doit consister en des DÉCLARATIONS DE THÈSE, pas des descriptions.

THÈSE — une déclaration clé qui révèle une partie du sujet.
Ne décrivez pas seulement, formulez des idées et arguments spécifiques.

STRUCTURE DES THÈSES :
- Diapositive 1 : Idée principale du sujet (déclaration centrale)
- Diapositives 2-{num_slides-1} : Aspects clés, avantages, applications
- Diapositive {num_slides} : Conclusion, avenir, point de vue

Chaque thèse doit :
✓ Être une déclaration spécifique directement liée à "{topic}"
✓ Contenir 2-3 phrases précises avec des DÉTAILS et EXEMPLES CONCRÉTS
✓ Développer le sujet principal
✓ Former une chaîne logique avec les autres thèses
✓ ÉVITER les phrases modèles comme "technologie clé", "ère numérique", "société moderne"
✓ Utiliser une TERMINOLOGIE SPÉCIFIQUE et des faits pertinents uniquement pour "{topic}"

Pour chaque diapositive, retournez JSON avec les champs :
- "title" : Titre bref (2-3 mots) spécifique au sujet
- "search_keyword" : Mots-clés pour recherche d'images en anglais (3-4 mots)
- "content" : THÈSE — déclaration spécifique (2-3 phrases avec détails)

EXEMPLE de thèses correctes pour "Chiens" :
{{
  "slides": [
    {{"title": "Évolution des Chiens", "search_keyword": "dog evolution wolf domestication", "content": "Les chiens descendent des loups il y a environ 15 000 ans par domestication. Les recherches génétiques montrent que les premiers chiens sont apparus en Asie de l'Est et se sont répandus dans le monde avec les humains. Les races modernes sont le résultat de l'élevage sélectif au cours des 200 dernières années."}},
    {{"title": "Races et Fonctions", "search_keyword": "dog breeds working dogs types", "content": "Plus de 400 races de chiens reconnues existent, chacune élevée pour des tâches spécifiques. Les races de berger (Border Collies, Bergers) gèrent les troupeaux, les races de chasse (Retrievers, Épagneuls) aident à la chasse, tandis que les races de garde (Dobermans, Rottweilers) protègent les propriétés. Les races de compagnie (Chihuahuas, Terriers) sont élevées exclusivement pour la compagnie."}},
    {{"title": "Intelligence Canine", "search_keyword": "dog intelligence training cognition", "content": "Les chiens peuvent mémoriser jusqu'à 165 mots et gestes, comparable aux capacités cognitives d'un enfant de deux ans. Les Border Collies sont considérés comme la race la plus intelligente, comprenant de nouvelles commandes après seulement 5 répétitions. Les recherches montrent que les chiens distinguent les émotions humaines par les expressions faciales et le ton de la voix."}}
  ]
}}

INCORRECT (phrases modèles) :
"Les chiens deviennent un facteur clé dans la société moderne. L'adoption de ces technologies débloque de nouvelles possibilités."

CORRECT (faits concrets) :
"Les chiens possèdent un sens de l'odorat 10 000 fois plus aigu que les humains grâce à 300 millions de récepteurs olfactifs. Cela leur permet de détecter des drogues, des explosifs et même de diagnostiquer le cancer à un stade précoce."

Retournez SEULEMENT du JSON valide sans texte supplémentaire.

CRITIQUE : 
- Chaque thèse doit contenir des FAITS CONCRÉTS, des NOMBRES, des EXEMPLES liés à "{topic}"
- N'utilisez PAS de phrases génériques sur "technologie", "innovation", "avenir" sans précisions
- Le titre et le contenu de chaque diapositive doivent être LIÉS LOGIQUEMENT
- Chaque search_keyword doit être DIFFÉRENT et spécifique"""
        else:  # Default to English
            prompt = f"""Create a structured presentation on the topic: "{topic}"
Number of slides: {num_slides}

IMPORTANT: The presentation must consist of THESIS STATEMENTS, not descriptions!
Use the structure below as a guide, but adapt it to the topic "{topic}".

THESIS — a key statement that reveals part of the topic.
Do NOT just describe; formulate specific ideas and arguments.

FORMAT REQUIREMENTS:
- Keep paragraphs concise (2-3 sentences)
- Return ONLY valid JSON with fields: title, search_keyword (English), content
"""


        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'system', 'content': f"{system_prompt}\n\nAlways respond with valid JSON only. Generate content in {language_name}."},
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


def create_fallback_slides(topic, num_slides, language='en'):
    """
    Create fallback slides if API fails with language support
    """
    slides = []
    
    # Language-specific fallback content
    if language == 'ru':
        slides.append({
            'title': f'{topic} изменяет мир',
            'search_keyword': f'{topic} innovation future technology',
            'content': f'{topic} становится ключевым фактором развития современного общества. Внедрение этих технологий открывает новые возможности для бизнеса и повседневной жизни. Понимание {topic} критически важно для успеха в цифровую эпоху.'
        })
        
        thesis_templates = [
            ('Ключевые преимущества', 'key benefits advantages', lambda t: f'{t} повышает эффективность работы и снижает издержки. Автоматизация процессов позволяет сосредоточиться на стратегических задачах. Компании, внедрившие {t}, получают конкурентное преимущество на рынке.'),
            ('Практическое применение', 'real world practical use', lambda t: f'Реальные кейсы показывают эффективность {t} в различных отраслях. От медицины до финансов, технология решает сложные задачи. Успешные примеры вдохновляют на дальнейшее внедрение.'),
            ('Вызовы и решения', 'challenges solutions problems', lambda t: f'Основные препятствия при внедрении {t} включают технические и организационные барьеры. Однако современные подходы позволяют эффективно преодолевать эти трудности. Правильная стратегия минимизирует риски и ускоряет адаптацию.'),
            ('Будущее технологии', 'future innovation development', lambda t: f'{t} будет играть всё более важную роль в ближайшие годы. Инвестиции в развитие этой области растут экспоненциально. Те, кто освоит {t} сегодня, станут лидерами завтрашнего дня.')
        ]
        
        for i in range(1, min(num_slides, len(thesis_templates) + 1)):
            title, keywords, content_func = thesis_templates[i - 1]
            slides.append({
                'title': title,
                'search_keyword': f'{topic} {keywords}',
                'content': content_func(topic)
            })
            
    elif language == 'es':
        slides.append({
            'title': f'{topic} Revoluciona',
            'search_keyword': f'{topic} innovacion futuro tecnologia',
            'content': f'{topic} está redefiniendo cómo abordamos los desafíos y oportunidades modernos. La adopción de estas tecnologías desbloquea nuevo potencial para negocios y vida diaria. Dominar {topic} es fundamental para el éxito en la era digital.'
        })
        
        thesis_templates = [
            ('Ventajas Clave', 'ventajas beneficios clave', lambda t: f'{t} mejora drásticamente la eficiencia mientras reduce costos operativos. La automatización permite a los equipos enfocarse en iniciativas estratégicas en lugar de tareas rutinarias. Las organizaciones que implementan {t} obtienen ventajas competitivas significativas en sus mercados.'),
            ('Impacto en el Mundo Real', 'impacto aplicaciones practicas', lambda t: f'Las historias de éxito demuestran la efectividad de {t} en diversas industrias. Desde la salud hasta las finanzas, la tecnología resuelve problemas anteriormente intratables. Estos ejemplos probados inspiran mayor adopción e innovación.'),
            ('Superando Desafíos', 'desafios soluciones problemas', lambda t: f'Los obstáculos principales para la adopción de {t} incluyen complejidad técnica y resistencia organizacional. Los marcos y metodologías modernos abordan efectivamente estas barreras. La planificación estratégica minimiza riesgos y acelera la implementación exitosa.'),
            ('Perspectiva Futura', 'futuro innovacion desarrollo', lambda t: f'{t} jugará un papel cada vez más vital en dar forma al mañana. La inversión en este campo crece exponencialmente año tras año. Los primeros adoptantes de {t} se posicionan como líderes del futuro.')
        ]
        
        for i in range(1, min(num_slides, len(thesis_templates) + 1)):
            title, keywords, content_func = thesis_templates[i - 1]
            slides.append({
                'title': title,
                'search_keyword': f'{topic} {keywords}',
                'content': content_func(topic)
            })
            
    elif language == 'zh':
        slides.append({
            'title': f'{topic} 革命',
            'search_keyword': f'{topic} innovation future technology',
            'content': f'{topic} 正在重塑我们应对现代挑战和机遇的方式。采用这些技术为业务和日常生活开启了新的可能性。掌握 {topic} 对于数字时代的成功至关重要。'
        })
        
        thesis_templates = [
            ('关键优势', 'key benefits advantages', lambda t: f'{t} 显著提高效率同时降低运营成本。自动化使团队能够专注于战略举措而非日常任务。实施 {t} 的组织在其市场中获得显著的竞争优势。'),
            ('现实世界影响', 'real world practical applications', lambda t: f'成功案例证明了 {t} 在不同行业的有效性。从医疗保健到金融，该技术解决了以前难以解决的问题。这些经过验证的例子激励着进一步的采用和创新。'),
            ('克服挑战', 'challenges solutions problems', lambda t: f'{t} 采用的主要障碍包括技术复杂性和组织阻力。现代框架和方法有效地解决了这些障碍。战略规划将风险降至最低并加速成功实施。'),
            ('未来展望', 'future innovation development', lambda t: f'{t} 将在塑造未来中发挥越来越重要的作用。该领域的投资正在逐年指数级增长。早期采用 {t} 的人将自己定位为未来的领导者。')
        ]
        
        for i in range(1, min(num_slides, len(thesis_templates) + 1)):
            title, keywords, content_func = thesis_templates[i - 1]
            slides.append({
                'title': title,
                'search_keyword': f'{topic} {keywords}',
                'content': content_func(topic)
            })
            
    elif language == 'fr':
        slides.append({
            'title': f'{topic} Révolution',
            'search_keyword': f'{topic} innovation future technologie',
            'content': f'{topic} redéfinit comment nous abordons les défis et opportunités modernes. L\'adoption de ces technologies débloque de nouvelles possibilités pour les entreprises et la vie quotidienne. Maîtriser {topic} est essentiel pour réussir à l\'ère numérique.'
        })
        
        thesis_templates = [
            ('Avantages Clés', 'avantages bénéfices clés', lambda t: f'{t} améliore drastiquement l\'efficacité tout en réduisant les coûts opérationnels. L\'automatisation permet aux équipes de se concentrer sur des initiatives stratégiques au lieu de tâches routinières. Les organisations implémentant {t} gagnent des avantages compétitifs significatifs sur leurs marchés.'),
            ('Impact Réel', 'impact applications pratiques', lambda t: f'Les histoires de réussite démontrent l\'efficacité de {t} dans diverses industries. De la santé aux finances, la technologie résout des problèmes auparavant intractables. Ces exemples éprouvés inspirent une adoption et une innovation supplémentaires.'),
            ('Surmonter les Défis', 'défis solutions problèmes', lambda t: f'Les obstacles principaux à l\'adoption de {t} incluent la complexité technique et la résistance organisationnelle. Les cadres et méthodologies modernes traitent efficacement ces barrières. La planification stratégique minimise les risques et accélère l\'implémentation réussie.'),
            ('Aperçu Futur', 'futur innovation développement', lambda t: f'{t} jouera un rôle de plus en plus vital dans façonner demain. L\'investissement dans ce domaine croît exponentiellement année après année. Les premiers adoptants de {t} se positionnent comme les leaders de l\'avenir.')
        ]
        
        for i in range(1, min(num_slides, len(thesis_templates) + 1)):
            title, keywords, content_func = thesis_templates[i - 1]
            slides.append({
                'title': title,
                'search_keyword': f'{topic} {keywords}',
                'content': content_func(topic)
            })
    else:  # Default to English
        slides.append({
            'title': f'{topic} Revolution',
            'search_keyword': f'{topic} innovation future technology',
            'content': f'{topic} is reshaping how we approach modern challenges and opportunities. The adoption of these technologies unlocks new potential for businesses and daily life. Mastering {topic} is critical for success in the digital age.'
        })
        
        thesis_templates = [
            ('Key Advantages', 'key benefits advantages', lambda t: f'{t} dramatically improves efficiency while reducing operational costs. Automation enables teams to focus on strategic initiatives instead of routine tasks. Organizations implementing {t} gain significant competitive advantages in their markets.'),
            ('Real-World Impact', 'real world practical applications', lambda t: f'Success stories demonstrate the effectiveness of {t} across diverse industries. From healthcare to finance, the technology solves previously intractable problems. These proven examples inspire further adoption and innovation.'),
            ('Overcoming Challenges', 'challenges solutions problems', lambda t: f'Primary obstacles to {t} adoption include technical complexity and organizational resistance. Modern frameworks and methodologies effectively address these barriers. Strategic planning minimizes risks and accelerates successful implementation.'),
            ('Future Outlook', 'future innovation development', lambda t: f'{t} will play an increasingly vital role in shaping tomorrow. Investment in this field is growing exponentially year over year. Early adopters of {t} position themselves as leaders of the future.')
        ]
        
        for i in range(1, min(num_slides, len(thesis_templates) + 1)):
            title, keywords, content_func = thesis_templates[i - 1]
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


# Theme color configurations for presentations
PRESENTATION_THEMES = {
    'light': {
        'background': RGBColor(245, 245, 250),
        'title_slide_bg': RGBColor(15, 25, 45),
        'content_slide_bg': RGBColor(245, 245, 250),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(30, 60, 120),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(40, 40, 40),
        'accent_color': RGBColor(30, 60, 180)
    },
    'dark': {
        'background': RGBColor(30, 30, 30),
        'title_slide_bg': RGBColor(15, 15, 25),
        'content_slide_bg': RGBColor(30, 30, 30),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(187, 134, 252),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(224, 224, 224),
        'accent_color': RGBColor(3, 218, 198)
    },
    'modern': {
        'background': RGBColor(250, 250, 250),
        'title_slide_bg': RGBColor(30, 30, 50),
        'content_slide_bg': RGBColor(250, 250, 250),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(79, 70, 229),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(15, 23, 42),
        'accent_color': RGBColor(124, 58, 237)
    },
    'casual': {
        'background': RGBColor(255, 245, 247),
        'title_slide_bg': RGBColor(76, 69, 105),
        'content_slide_bg': RGBColor(255, 245, 247),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(255, 107, 157),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(51, 51, 51),
        'accent_color': RGBColor(255, 160, 122)
    },
    'classic': {
        'background': RGBColor(236, 240, 241),
        'title_slide_bg': RGBColor(28, 38, 50),
        'content_slide_bg': RGBColor(236, 240, 241),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(44, 62, 80),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(44, 62, 80),
        'accent_color': RGBColor(52, 73, 94)
    },
    'futuristic': {
        'background': RGBColor(10, 14, 39),
        'title_slide_bg': RGBColor(10, 14, 39),
        'content_slide_bg': RGBColor(10, 14, 39),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(0, 212, 255),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(255, 255, 255),
        'accent_color': RGBColor(255, 0, 255)
    },
    'minimal': {
        'background': RGBColor(255, 255, 255),
        'title_slide_bg': RGBColor(0, 0, 0),
        'content_slide_bg': RGBColor(255, 255, 255),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(0, 0, 0),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(0, 0, 0),
        'accent_color': RGBColor(102, 102, 102)
    },
    'gradient': {
        'background': RGBColor(254, 249, 255),
        'title_slide_bg': RGBColor(79, 30, 85),
        'content_slide_bg': RGBColor(254, 249, 255),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(240, 147, 251),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(51, 51, 51),
        'accent_color': RGBColor(79, 172, 254)
    },
    'glassmorphism': {
        'background': RGBColor(102, 126, 234),
        'title_slide_bg': RGBColor(26, 30, 74),
        'content_slide_bg': RGBColor(102, 126, 234),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(255, 255, 255),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(255, 255, 255),
        'accent_color': RGBColor(255, 255, 255)
    },
    'nature': {
        'background': RGBColor(241, 250, 238),
        'title_slide_bg': RGBColor(29, 67, 50),
        'content_slide_bg': RGBColor(241, 250, 238),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(45, 106, 79),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(27, 67, 50),
        'accent_color': RGBColor(82, 183, 136)
    },
    'vivid': {
        'background': RGBColor(255, 252, 242),
        'title_slide_bg': RGBColor(33, 5, 17),
        'content_slide_bg': RGBColor(255, 252, 242),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(255, 0, 110),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(33, 37, 41),
        'accent_color': RGBColor(251, 86, 7)
    },
    'business': {
        'background': RGBColor(248, 250, 252),
        'title_slide_bg': RGBColor(15, 25, 50),
        'content_slide_bg': RGBColor(248, 250, 252),
        'title_color_first_last': RGBColor(255, 255, 255),
        'title_color_content': RGBColor(30, 58, 138),
        'content_color_first_last': RGBColor(255, 255, 255),
        'content_color_content': RGBColor(15, 23, 42),
        'accent_color': RGBColor(14, 165, 233)
    }
}

def create_presentation(topic, slides_data, theme='light'):
    """
    Create PowerPoint presentation with text and images
    """
    print(f"\n{'#'*60}")
    print(f"# Creating presentation: {topic}")
    print(f"# Total slides: {len(slides_data)}")
    print(f"# Theme: {theme}")
    print(f"{'#'*60}\n")
    
    # Get theme configuration
    theme_config = PRESENTATION_THEMES.get(theme, PRESENTATION_THEMES['light'])
    
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
        
        # Set background color based on theme
        background = slide.background
        fill = background.fill
        fill.solid()
        
        is_title_slide = (idx == 0)
        is_last_slide = (idx == len(slides_data) - 1)
        
        if is_title_slide or is_last_slide:
            fill.fore_color.rgb = theme_config['title_slide_bg']
        else:
            fill.fore_color.rgb = theme_config['content_slide_bg']
        
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
        title_para.font.name = 'Roboto'
        
        # Calculate optimal font size to fit title in one line
        optimal_font_size = calculate_title_font_size(
            text=slide_data['title'],
            max_width_inches=8.5,
            bold=True
        )
        
        if is_title_slide or is_last_slide:
            title_para.font.size = Pt(optimal_font_size)
            title_para.font.bold = True
            title_para.font.color.rgb = theme_config['title_color_first_last']
        else:
            title_para.font.size = Pt(optimal_font_size)
            title_para.font.bold = True
            title_para.font.color.rgb = theme_config['title_color_content']
        
        # Add accent element for content slides based on theme
        if not (is_title_slide or is_last_slide):
            try:
                slide.shapes.add_shape(
                    MSO_AUTO_SHAPE_TYPE.RECTANGLE,
                    Inches(0.3), Inches(0.3), Inches(0.1), Inches(5.0)
                ).fill.fore_color.rgb = theme_config['accent_color']
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
        
        # Add content text (description) with length limit
        content_text = slide_data['content']
        if len(content_text) > 500:
            content_text = content_text[:500] + "..."
        content_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(1.4),
            Inches(4.8), Inches(3.6)
        )
        content_frame = content_box.text_frame
        content_frame.word_wrap = True
        content_frame.text = content_text
        
        # Format content text based on theme
        # Dynamic font size based on content length
        content_length = len(content_text)
        if content_length > 250:
            base_font_size = 14
        elif content_length > 180:
            base_font_size = 15
        else:
            base_font_size = 16
        
        for paragraph in content_frame.paragraphs:
            paragraph.font.name = 'Roboto'
            paragraph.font.size = Pt(base_font_size if not (is_title_slide or is_last_slide) else 20)
            if is_title_slide or is_last_slide:
                paragraph.font.color.rgb = theme_config['content_color_first_last']
            else:
                paragraph.font.color.rgb = theme_config['content_color_content']
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
        language = data.get('language', 'en')  # Get language from frontend
        theme = data.get('theme', 'light')  # Get theme from frontend
        presentation_type = data.get('presentation_type', 'business')  # Get presentation type
        
        # Validation
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        # Normalize slides count to default 10 if out of range
        try:
            num_slides = int(num_slides)
        except (ValueError, TypeError):
            num_slides = 10
        if num_slides < 3 or num_slides > 10:
            num_slides = 10
        
        # Check API keys
        if not OPENAI_API_KEY:
            return jsonify({'error': 'OpenAI API key not configured'}), 500
        
        if not PEXELS_API_KEY:
            return jsonify({'error': 'Pexels API key not configured'}), 500
        
        # Generate slide content in the selected language
        print(f"Generating content for topic: {topic}, slides: {num_slides}, language: {language}, type: {presentation_type}")
        slides_data = generate_slide_content_in_language(topic, num_slides, language, presentation_type)
        
        if not slides_data:
            # Use fallback slides in the selected language
            print("Using fallback slides in selected language")
            slides_data = create_fallback_slides(topic, num_slides, language)
            if not slides_data:
                return jsonify({'error': 'Failed to generate slide content'}), 502
        
        # Ensure we have the right number of slides
        slides_data = slides_data[:num_slides]
        
        # Create presentation with the selected theme
        print("Creating presentation with theme:", theme)
        filepath = create_presentation(topic, slides_data, theme)
        filename = os.path.basename(filepath)
        
        # Save presentation to database if user is authenticated
        if current_user.is_authenticated:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    '''INSERT INTO presentations (user_id, topic, num_slides, filename, presentation_type) 
                       VALUES (?, ?, ?, ?, ?)''',
                    (current_user.id, topic, num_slides, filename, presentation_type)
                )
                conn.commit()
                conn.close()
                print(f"✅ Presentation saved to database for user {current_user.id}")
            except Exception as e:
                print(f"⚠️ Error saving presentation to database: {e}")
        
        return jsonify({
            'success': True,
            'filename': filename,
            'slides': slides_data,
            'presentation_type': presentation_type
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


@app.route('/api/presentation-types', methods=['GET'])
def get_presentation_types():
    """
    API endpoint to get all available presentation types
    """
    return jsonify({
        'success': True,
        'types': PRESENTATION_TYPES
    })


# Admin routes
@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard - only accessible to authenticated admins"""
    if not is_admin():
        flash('Access denied. Administrator privileges required.', 'error')
        return redirect(url_for('admin_login'))
    return render_template('admin/dashboard.html')

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    """Admin users management page - only accessible to authenticated admins"""
    if not is_admin():
        flash('Access denied. Administrator privileges required.', 'error')
        return redirect(url_for('admin_login'))
    
    # Handle POST requests for user actions
    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')
        
        if action == 'delete_user' and user_id:
            # Delete user
            if delete_user(user_id):
                flash('✅ User deleted successfully.', 'success')
            else:
                flash('❌ Error: Failed to delete user. Please try again.', 'error')
        elif action == 'update_status' and user_id:
            # Update user status
            status = request.form.get('status')
            if status in ['active', 'blocked']:
                if update_user_status(user_id, status):
                    status_text = 'activated' if status == 'active' else 'blocked'
                    flash(f'✅ User status updated: {status_text}.', 'success')
                else:
                    flash('❌ Error: Failed to update user status.', 'error')
            else:
                flash('❌ Invalid status value.', 'error')
        
        # Preserve search and pagination parameters
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        return redirect(url_for('admin_users', search=search, page=page))
    
    # GET request - display users with pagination and search
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 15  # Users per page
    
    # Get filtered users
    all_users = get_all_users()
    
    # Apply search filter
    if search_query:
        filtered_users = [
            user for user in all_users
            if search_query.lower() in user['email'].lower() or 
               search_query.lower() in user['status'].lower()
        ]
    else:
        filtered_users = all_users
    
    # Calculate pagination
    total_users = len(filtered_users)
    total_pages = max(1, (total_users + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))  # Ensure page is in valid range
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_users = filtered_users[start_idx:end_idx]
    
    return render_template(
        'admin/users.html',
        users=paginated_users,
        total_users=total_users,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        search_query=search_query
    )

# Firebase Authentication routes
@app.route('/auth/firebase/', methods=['POST'])
def firebase_auth_route():
    """Handle Firebase authentication"""
    try:
        data = request.get_json()
        id_token = data.get('token')
        
        if not id_token:
            return jsonify({'error': 'Token is required'}), 400
        
        # Verify Firebase ID token
        try:
            decoded_token = firebase_auth.verify_id_token(id_token)
        except Exception as e:
            print(f"Firebase token verification error: {e}")
            return jsonify({'error': 'Invalid token'}), 401
        
        firebase_uid = decoded_token['uid']
        email = decoded_token.get('email')
        name = decoded_token.get('name', '')
        picture = decoded_token.get('picture', '')
        
        if not email:
            return jsonify({'error': 'Email not found in token'}), 400
        
        # Get or create user
        user_data, error = get_or_create_firebase_user(firebase_uid, email, name, picture)
        if error:
            return jsonify({'error': error}), 500
        
        if user_data['status'] == 'blocked':
            return jsonify({'error': 'Your account has been blocked. Please contact support.'}), 403
        
        # Login user
        user = User(
            user_data['id'],
            email=user_data['email'],
            is_admin_user=False,
            name=user_data.get('name'),
            picture=user_data.get('picture')
        )
        login_user(user, remember=True)
        
        return jsonify({
            'success': True,
            'message': 'Logged in successfully',
            'redirect': url_for('user_dashboard')
        })
        
    except Exception as e:
        print(f"Firebase auth error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

# User authentication routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration page"""
    if current_user.is_authenticated:
        # If already logged in, redirect to dashboard
        if hasattr(current_user, 'is_admin_user') and current_user.is_admin_user:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Validate email
        is_valid_email, email_error = validate_email(email)
        if not is_valid_email:
            flash(f'❌ {email_error}', 'error')
            return render_template('signup.html')
        
        # Validate password
        is_valid_password, password_error = validate_password(password)
        if not is_valid_password:
            flash(f'❌ {password_error}', 'error')
            return render_template('signup.html')
        
        # Check password confirmation
        if password != password_confirm:
            flash('❌ Passwords do not match', 'error')
            return render_template('signup.html')
        
        # Create user
        user_id, error = create_user(email, password)
        if error:
            flash(f'❌ {error}', 'error')
            return render_template('signup.html')
        
        # Auto-login after registration
        user_data = get_user_by_id(user_id)
        if user_data:
            user = User(
                user_data['id'], 
                email=user_data['email'], 
                is_admin_user=False,
                name=user_data.get('name'),
                picture=user_data.get('picture')
            )
            login_user(user)
            flash('✅ Account created successfully! Welcome to AI SlideRush!', 'success')
            return redirect(url_for('user_dashboard'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        # If already logged in, redirect to appropriate dashboard
        if hasattr(current_user, 'is_admin_user') and current_user.is_admin_user:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('❌ Please enter both email and password', 'error')
            return render_template('login.html')
        
        # Authenticate user
        user_data, error = authenticate_user(email, password)
        if error:
            flash(f'❌ {error}', 'error')
            return render_template('login.html')
        
        # Login user
        user = User(
            user_data['id'], 
            email=user_data['email'], 
            is_admin_user=False,
            name=user_data.get('name'),
            picture=user_data.get('picture')
        )
        login_user(user, remember=True)
        flash('✅ Logged in successfully!', 'success')
        
        # Redirect to next page or dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('user_dashboard'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('✅ You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def user_dashboard():
    """User dashboard - personal cabinet"""
    # Redirect admins to admin dashboard
    if hasattr(current_user, 'is_admin_user') and current_user.is_admin_user:
        return redirect(url_for('admin_dashboard'))
    
    # Get search, filter and pagination parameters
    search_query = request.args.get('search', '').strip()
    filter_type = request.args.get('type', '').strip()  # Filter by presentation type
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    # Get user's presentations
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get total count for stats
        cursor.execute(
            'SELECT COUNT(*) as count FROM presentations WHERE user_id = ?',
            (current_user.id,)
        )
        total_presentations = cursor.fetchone()['count']
        
        # Build query with search and type filter
        query = 'SELECT * FROM presentations WHERE user_id = ?'
        params = [current_user.id]
        
        if search_query:
            query += ' AND topic LIKE ?'
            params.append(f'%{search_query}%')
        
        if filter_type and filter_type in PRESENTATION_TYPES:
            query += ' AND presentation_type = ?'
            params.append(filter_type)
        
        query += ' ORDER BY creation_date DESC'
        
        cursor.execute(query, params)
        all_presentations = [dict(row) for row in cursor.fetchall()]
        
        # Add presentation type info to each presentation
        for pres in all_presentations:
            if not pres.get('presentation_type'):
                pres['presentation_type'] = 'business'  # Default for old presentations
            pres['type_info'] = get_presentation_type_info(pres['presentation_type'])
        
        # Get user data
        cursor.execute('SELECT * FROM users WHERE id = ?', (current_user.id,))
        user_data = dict(cursor.fetchone()) if cursor.fetchone() else None
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (current_user.id,))
        user_data = dict(cursor.fetchone())
        
        conn.close()
    except Exception as e:
        print(f"Error fetching presentations: {e}")
        all_presentations = []
        total_presentations = 0
        user_data = None
    
    # Calculate pagination
    total_filtered = len(all_presentations)
    total_pages = max(1, (total_filtered + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_presentations = all_presentations[start_idx:end_idx]
    
    return render_template(
        'dashboard.html',
        presentations=paginated_presentations,
        total_presentations=total_presentations,
        user_data=user_data,
        page=page,
        total_pages=total_pages,
        search_query=search_query,
        filter_type=filter_type,
        presentation_types=PRESENTATION_TYPES
    )

@app.route('/presentation/delete', methods=['POST'])
@login_required
def delete_presentation():
    """Delete user's presentation"""
    # Redirect admins
    if hasattr(current_user, 'is_admin_user') and current_user.is_admin_user:
        flash('❌ Admins cannot delete presentations from user dashboard', 'error')
        return redirect(url_for('admin_dashboard'))
    
    presentation_id = request.form.get('presentation_id')
    if not presentation_id:
        flash('❌ Invalid request', 'error')
        return redirect(url_for('user_dashboard'))
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verify ownership
        cursor.execute(
            'SELECT * FROM presentations WHERE id = ? AND user_id = ?',
            (presentation_id, current_user.id)
        )
        presentation = cursor.fetchone()
        
        if not presentation:
            conn.close()
            flash('❌ Presentation not found or access denied', 'error')
            return redirect(url_for('user_dashboard'))
        
        # Delete presentation
        cursor.execute('DELETE FROM presentations WHERE id = ?', (presentation_id,))
        conn.commit()
        conn.close()
        
        flash('✅ Presentation deleted successfully', 'success')
    except Exception as e:
        print(f"Error deleting presentation: {e}")
        flash('❌ Error deleting presentation', 'error')
    
    # Preserve search and pagination
    search = request.form.get('search', '')
    page = request.form.get('page', 1, type=int)
    
    return redirect(url_for('user_dashboard', search=search, page=page))

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    # Redirect admins
    if hasattr(current_user, 'is_admin_user') and current_user.is_admin_user:
        flash('❌ Admins cannot edit profile from user dashboard', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Get user data
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (current_user.id,))
        user_data = dict(cursor.fetchone())
        conn.close()
    except Exception as e:
        print(f"Error fetching user data: {e}")
        user_data = None
    
    if request.method == 'POST':
        # Only allow password change for non-Google users
        if user_data and not user_data.get('google_id'):
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if current_password or new_password or confirm_password:
                # Validate current password
                if not current_password:
                    flash('❌ Please enter your current password', 'error')
                    return render_template('profile_edit.html', user_data=user_data)
                
                # Verify current password
                if not check_password_hash(user_data['password_hash'], current_password):
                    flash('❌ Current password is incorrect', 'error')
                    return render_template('profile_edit.html', user_data=user_data)
                
                # Validate new password
                is_valid, error_msg = validate_password(new_password)
                if not is_valid:
                    flash(f'❌ {error_msg}', 'error')
                    return render_template('profile_edit.html', user_data=user_data)
                
                # Check password confirmation
                if new_password != confirm_password:
                    flash('❌ New passwords do not match', 'error')
                    return render_template('profile_edit.html', user_data=user_data)
                
                # Update password
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    new_password_hash = generate_password_hash(new_password)
                    cursor.execute(
                        'UPDATE users SET password_hash = ? WHERE id = ?',
                        (new_password_hash, current_user.id)
                    )
                    conn.commit()
                    conn.close()
                    
                    flash('✅ Password updated successfully!', 'success')
                    return redirect(url_for('user_dashboard'))
                except Exception as e:
                    print(f"Error updating password: {e}")
                    flash('❌ Error updating password', 'error')
        else:
            flash('ℹ️ No changes to save', 'error')
    
    return render_template('profile_edit.html', user_data=user_data)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if user exists and password is correct
        if username in ADMIN_USERS and check_password_hash(ADMIN_USERS[username]['password_hash'], password):
            user = User(username, is_admin_user=True)
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    """Admin logout"""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin_login'))


# Application entry point - MUST BE AT THE END OF FILE
if __name__ == '__main__':
    print("Starting Presentation Service...")
    print(f"OpenAI API Key configured: {bool(OPENAI_API_KEY)}")
    print(f"Pexels API Key configured: {bool(PEXELS_API_KEY)}")
    print(f"LibreTranslate enabled: {LIBRETRANSLATE_ENABLED}")
    print(f"LibreTranslate URL: {LIBRETRANSLATE_URL}")
    print(f"LibreTranslate reachable: {is_libretranslate_available()}")
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting on port: {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
