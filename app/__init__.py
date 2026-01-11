import sentry_sdk
import os
import logging
import json
import socket
from flask import Flask, redirect, url_for, request, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_admin import Admin
from flask_admin.base import MenuLink
from flask_admin.contrib.sqla import ModelView
from werkzeug.exceptions import abort
from datetime import datetime
from markupsafe import Markup
from flask_caching import Cache
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_assets import Environment, Bundle
from flask_mail import Mail
from config import config
from logging.handlers import SMTPHandler, RotatingFileHandler
from celery import Celery
from slugify import slugify

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
cache = Cache()
migrate = Migrate()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address, default_limits=["200 per day", "50 per hour"]
)
assets = Environment()
mail = Mail()
celery = Celery(
    __name__,
    broker=os.environ.get("CELERY_BROKER_URL"),
    backend=os.environ.get("CELERY_RESULT_BACKEND"),
)


class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))
        abort(403)


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize Sentry for error tracking
    if app.config.get("SENTRY_DSN"):
        sentry_sdk.init(
            dsn=app.config["SENTRY_DSN"],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
        )
    
    # <--- 2. ДОБАВИТЬ ЭТУ СТРОКУ (Регистрация фильтра)
    app.jinja_env.filters['slugify'] = slugify 

    # Health check endpoint
    @app.route("/health")
    def health_check():
        """Health check endpoint for load balancers and monitoring"""
        health_status = {
            "status": "healthy",
            "version": "1.0.0",
            "database": "unknown",
            "cache": "unknown",
        }
        
        # Check database connection
        try:
            db.session.execute(db.text("SELECT 1"))
            health_status["database"] = "connected"
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"
        
        # Check cache connection
        try:
            cache.get("health_check_key")
            health_status["cache"] = "connected"
        except Exception as e:
            health_status["cache"] = f"error: {str(e)}"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return jsonify(health_status), status_code

    if not app.config["DEBUG"] and not app.config["TESTING"]:
        Talisman(app, content_security_policy=None)  # CSP can be customized per need
    db.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Configure rate limiting with Redis storage
    from flask_limiter import Redis
    try:
        redis_client = Redis.from_url(app.config["CACHE_REDIS_URL"])
        limiter.storage_uri = app.config["CACHE_REDIS_URL"]
    except Exception:
        pass  # Fall back to in-memory storage if Redis is not available
    
    limiter.init_app(app)
    assets.init_app(app)
    mail.init_app(app)
    celery.conf.update(app.config)
    css_bundle = Bundle("css/style.css", filters="cssmin", output="gen/packed.css")
    js_bundle = Bundle(
        "js/main.js", "js/cart.js", filters="jsmin", output="gen/packed.js"
    )
    assets.register("css_all", css_bundle)
    assets.register("js_all", js_bundle)

    # ... (далее код без изменений) ...
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir, exist_ok=True)
            
        file_handler = RotatingFileHandler(
            "logs/megamart.log", maxBytes=10240, backupCount=10
        )
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Logstash handler for ELK integration
        logstash_host = os.environ.get("LOGSTASH_HOST", "localhost")
        logstash_port = int(os.environ.get("LOGSTASH_PORT", 5044))
        
        class LogstashHandler(logging.Handler):
            """Custom handler to send logs to Logstash via TCP"""
            def __init__(self, host, port):
                super().__init__()
                self.host = host
                self.port = port
                self.socket = None
                
            def emit(self, record):
                try:
                    log_entry = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": self.format(record),
                        "pathname": record.pathname,
                        "lineno": record.lineno,
                        "func": record.funcName,
                        "service": "megamart",
                        "environment": app.config.get("FLASK_CONFIG", "unknown"),
                        "hostname": socket.gethostname(),
                        "app_version": "1.0.0",
                    }
                    
                    # Добавляем extra поля если есть
                    if hasattr(record, "user_id"):
                        log_entry["user_id"] = record.user_id
                    if hasattr(record, "request_id"):
                        log_entry["request_id"] = record.request_id
                        
                    import json
                    msg = json.dumps(log_entry) + "\n"
                    
                    # Создаем сокет только когда нужно отправить
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    sock.connect((self.host, self.port))
                    sock.sendall(msg.encode())
                    sock.close()
                except Exception:
                    pass  # Игнорируем ошибки отправки логов
        
        try:
            logstash_handler = LogstashHandler(logstash_host, logstash_port)
            logstash_handler.setLevel(logging.ERROR)
            app.logger.addHandler(logstash_handler)
        except Exception:
            pass  # Logstash может быть недоступен
        
        if app.config["MAIL_SERVER"]:
            auth = None
            if app.config["MAIL_USERNAME"] or app.config["MAIL_PASSWORD"]:
                auth = (app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
            secure = None
            if app.config["MAIL_USE_TLS"]:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config["MAIL_SERVER"], app.config["MAIL_PORT"]),
                fromaddr="no-reply@" + app.config["MAIL_SERVER"],
                toaddrs=app.config["ADMINS"],
                subject="[MegaMart] Сбой в системе",
                credentials=auth,
                secure=secure,
            )
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("MegaMart startup")

    from .models import (
        User,
        Category,
        Brand,
        Product,
        Order,
        OrderItem,
        Cart,
        ProductImage,
        PromoCode,
        Review,
    )

    class ProductAdminView(SecureModelView):
        def _image_preview_formatter(view, context, model, name):
            first_image = (
                ProductImage.query.filter_by(product_id=model.id)
                .order_by(ProductImage.sort_order)
                .first()
            )
            if first_image:
                return Markup(
                    f'<img src="/static/images/{first_image.image_url}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;">'
                )
            return Markup(
                '<img src="/static/images/default_product.png" style="width: 50px; height: 50px; object-fit: cover;">'
            )

        column_formatters = {"images": _image_preview_formatter}
        column_list = ("id", "name", "slug", "price", "in_stock", "category", "images")
        column_labels = {
            "images": "Фото",
            "name": "Название",
            "slug": "URL (Slug)",
            "price": "Цена",
            "old_price": "Старая цена",
            "in_stock": "В наличии",
            "category": "Категория",
            "brand": "Бренд",
            "sku": "Артикул",
            "description": "Описание",
            "meta_title": "Meta Title",
            "meta_description": "Meta Description",
        }
        column_searchable_list = ["name", "sku", "description", "slug"]
        column_sortable_list = ["name", "price", "in_stock"]
        page_size = 20

        def _price_formatter(view, context, model, name):
            price = getattr(model, name)
            if price is None:
                return "-"
            return f"{price:.2f} ₽"

        column_formatters.update(
            {"price": _price_formatter, "old_price": _price_formatter}
        )

        form_columns = [
            "name",
            "slug",
            "sku",
            "description",
            "price",
            "old_price",
            "in_stock",
            "category",
            "brand",
            "meta_title",
            "meta_description",
            "country",        # Добавлено для админки
            "warranty",       # Добавлено для админки
            "specifications", # Добавлено для админки
        ]

        inline_models = [
            (
                ProductImage,
                {
                    "form_columns": ["image_url", "sort_order"],
                    "form_label": "Изображения товара",
                    "column_labels": {"image_url": "Файл", "sort_order": "Порядок"},
                    "max_entries": 6,
                    "min_entries": 0,
                },
            )
        ]

    class CategoryAdminView(SecureModelView):
        form_columns = ["name", "slug", "parent_id", "meta_title", "meta_description"]

    from .admin_views import CustomAdminIndexView, ImportExportView

    admin = Admin(
        app,
        name="MegaMart Admin",
        url="/admin-panel",
        index_view=CustomAdminIndexView(),
    )
    admin.base_template = "admin/master.html"
    admin.add_view(
        ProductAdminView(Product, db.session, name="Товары", category="Каталог")
    )
    admin.add_view(
        SecureModelView(User, db.session, name="Пользователи", category="Магазин")
    )
    admin.add_view(
        CategoryAdminView(Category, db.session, name="Категории", category="Каталог")
    )
    admin.add_view(
        SecureModelView(Brand, db.session, name="Бренды", category="Каталог")
    )
    admin.add_view(
        SecureModelView(Order, db.session, name="Заказы", category="Магазин")
    )
    admin.add_view(
        SecureModelView(OrderItem, db.session, name="Детали заказа", category="Магазин")
    )
    admin.add_view(
        SecureModelView(Cart, db.session, name="Корзины", category="Магазин")
    )
    admin.add_view(
        SecureModelView(PromoCode, db.session, name="Промокоды", category="Магазин")
    )
    admin.add_view(
        SecureModelView(Review, db.session, name="Отзывы", category="Каталог")
    )
    admin.add_view(
        ImportExportView(
            name="Импорт/Экспорт", endpoint="import-export", category="Инструменты"
        )
    )
    admin.add_link(MenuLink(name="Выйти", url="/auth/logout", category="Навигация"))
    admin.add_link(MenuLink(name="На главную MegaMart", url="/", category="Навигация"))

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        from .main import main_bp

        app.register_blueprint(main_bp)
        from .auth import auth_bp

        app.register_blueprint(auth_bp, url_prefix="/auth")
        from .cart import cart_app

        app.register_blueprint(cart_app, url_prefix="/cart")
        from .api import api_bp

        app.register_blueprint(api_bp, url_prefix="/api")
        app.jinja_env.globals.update(now=datetime.now)
        db.create_all()

    return app