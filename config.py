import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    # Общие настройки
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set in environment variables for production!")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    GOOGLE_ANALYTICS_ID = os.environ.get("GOOGLE_ANALYTICS_ID")

    # Настройки приложения
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

    # Настройки кэша
    CACHE_TYPE = os.environ.get("CACHE_TYPE") or "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL") or "redis://redis:6379/0"

    # YooKassa
    YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID")
    YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY")

    # Настройки для отправки email
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 25)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") is not None
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = ("MegaMart", os.environ.get("MAIL_USERNAME"))
    ADMINS = ["admin@megamart.com"]

    # Настройки Celery
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL") or "redis://redis:6379/0"
    CELERY_RESULT_BACKEND = (
        os.environ.get("CELERY_RESULT_BACKEND") or "redis://redis:6379/0"
    )

    # Sentry DSN для мониторинга ошибок
    SENTRY_DSN = os.environ.get("SENTRY_DSN")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DEV_DATABASE_URI"
    ) or "sqlite:///" + os.path.join(basedir, "dev.db")


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI")

    # Connection Pooling для production
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE") or 10),
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW") or 20),
    }

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": ProductionConfig,
}
