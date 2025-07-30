import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "change_me_to_secure_key")
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "your_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "your_pass")
    DB_NAME = os.getenv("DB_NAME", "mobility_bot")
    
    # LLM
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # App
    FEEDBACK_FORM_URL = os.getenv("FEEDBACK_FORM_URL", 
        "https://docs.google.com/forms/d/e/1FAIpQLSfT5gGcFuzE_9O1Vca545YmJ83wwzDy-4ZEoerhILOuyNmKWw/viewform")
    
    # Performance
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max request size
    SEND_FILE_MAX_AGE_DEFAULT = 3600  # 1 hour cache for static files

config = Config()