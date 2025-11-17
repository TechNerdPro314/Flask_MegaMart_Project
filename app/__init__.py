from flask import Flask, redirect, url_for, request, flash, abort, send_from_directory
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
import os

# --- Инициализация расширений ---
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = (
    "auth.login"  # Обновлено: указывает на blueprint 'auth' и view 'login'
)
login_manager.login_message_category = "info"
cache = Cache()
migrate = Migrate()
csrf = CSRFProtect()


# --- Класс для защиты представлений МОДЕЛЕЙ ---
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        if not current_user.is_authenticated:
            # Обновлено: указывает на blueprint 'auth'
            return redirect(url_for("auth.login", next=request.url))
        abort(403)


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Инициализация расширений с приложением
    db.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from .models import (
        User,
        Category,
        Brand,
        Product,
        Order,
        OrderItem,
        Cart,
        ProductImage,
    )

    # --- Админка ---
    class ProductImageAdminView(SecureModelView):
        pass

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
        column_list = ("id", "name", "price", "in_stock", "category", "brand", "images")
        column_labels = {
            "images": "Фото",
            "name": "Название",
            "price": "Цена",
            "old_price": "Старая цена",
            "in_stock": "В наличии",
            "category": "Категория",
            "brand": "Бренд",
            "sku": "Артикул",
            "description": "Описание",
        }
        column_searchable_list = ["name", "sku", "description"]
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

    from .admin_views import CustomAdminIndexView

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
        SecureModelView(Category, db.session, name="Категории", category="Каталог")
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

    admin.add_link(
        MenuLink(name="Выйти", url="/auth/logout", category="Навигация")
    )  # Обновлено
    admin.add_link(MenuLink(name="На главную MegaMart", url="/", category="Навигация"))

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        # --- Регистрация Blueprints ---
        # ИСПРАВЛЕНО: импортируем blueprint'ы из пакетов, а не из routes файлов
        from .main import main_bp

        app.register_blueprint(main_bp)

        from .auth import auth_bp

        app.register_blueprint(auth_bp, url_prefix="/auth")

        from .cart import cart_bp

        app.register_blueprint(cart_bp, url_prefix="/cart")

        from .api import api_bp

        app.register_blueprint(api_bp, url_prefix="/api")

        app.jinja_env.globals.update(now=datetime.now)
        # Старый импорт 'from . import routes' УДАЛЕН
        db.create_all()

    return app
