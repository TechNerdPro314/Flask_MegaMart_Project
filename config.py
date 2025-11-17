import os
from dotenv import load_dotenv

# Определяем базовую директорию проекта
basedir = os.path.abspath(os.path.dirname(__file__))
# Загружаем переменные окружения из файла .env
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    # Безопасность
    SECRET_KEY = os.environ.get("SECRET_KEY") or "a-very-insecure-default-key"
    WTF_CSRF_ENABLED = True

    # База данных
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Настройки приложения
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

    # Настройки кэша
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300

    # YooKassa
    YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID")
    YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY")
