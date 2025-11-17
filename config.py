import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    WTF_CSRF_ENABLED = True
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    SECRET_KEY = '1234567890supersecretkey'
    
    # MySQL
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:root@localhost/megamart_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True 

    # Настройки кэша (убирает предупреждение)
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300

    # YooKassa
    YOOKASSA_SHOP_ID = 'YOUR_SHOP_ID_HERE'
    YOOKASSA_SECRET_KEY = 'YOUR_SECRET_KEY_HERE'