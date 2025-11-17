from flask import (
    render_template,
    request,
    url_for,
    make_response,
    current_app,
    render_template_string,
)
from app import db, cache
from app.models import Product, Category, Brand, ProductImage
from datetime import datetime
from . import main_bp


def add_first_image_to_products(products):
    """Добавляет первое изображение к каждому товару в списке"""
    for product in products:
        first_image = (
            ProductImage.query.filter_by(product_id=product.id)
            .order_by(ProductImage.sort_order)
            .first()
        )
        product.first_image = (
            first_image.image_url if first_image else "default_product.png"
        )
    return products


@main_bp.route("/")
@main_bp.route("/index")
def index():
    categories = Category.query.order_by(Category.name).limit(6).all()
    featured_products = (
        Product.query.options(
            db.joinedload(Product.category), db.joinedload(Product.brand)
        )
        .order_by(Product.id.desc())
        .limit(8)
        .all()
    )
    featured_products = add_first_image_to_products(featured_products)
    return render_template(
        "index.html",
        title="Главная",
        categories=categories,
        featured_products=featured_products,
    )


@main_bp.route("/catalog")
def catalog():
    page = request.args.get("page", 1, type=int)
    per_page = 24

    category_id = request.args.get("category_id", type=int)
    brand_id = request.args.get("brand_id", type=int)
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    search_query = request.args.get("search_query", type=str)
    sort_by = request.args.get("sort_by", "price_asc")

    query = Product.query.options(
        db.joinedload(Product.category), db.joinedload(Product.brand)
    )

    if category_id:
        query = query.filter(Product.category_id == category_id)
    if brand_id:
        query = query.filter(Product.brand_id == brand_id)
    if min_price is not None and min_price >= 0:
        query = query.filter(Product.price >= min_price)
    if max_price is not None and max_price >= 0:
        query = query.filter(Product.price <= max_price)
    if search_query:
        query = query.filter(Product.name.ilike(f"%{search_query}%"))

    if sort_by == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort_by == "name_asc":
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.price.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    products = add_first_image_to_products(products)

    all_categories = Category.query.all()
    all_brands = Brand.query.all()

    return render_template(
        "catalog.html",
        title="Каталог",
        products=products,
        pagination=pagination,
        all_categories=all_categories,
        all_brands=all_brands,
        current_category_id=category_id,
        current_brand_id=brand_id,
        current_min_price=min_price,
        current_max_price=max_price,
        current_search_query=search_query,
        current_sort_by=sort_by,
    )


@main_bp.route("/product/<int:product_id>")
def product(product_id):
    prod = Product.query.options(
        db.joinedload(Product.category), db.joinedload(Product.brand)
    ).get_or_404(product_id)
    images = (
        ProductImage.query.filter_by(product_id=product_id)
        .order_by(ProductImage.sort_order)
        .all()
    )
    return render_template("product.html", title=prod.name, product=prod, images=images)


@main_bp.route("/about")
def about():
    return render_template("about.html", title="О нас")


@main_bp.route("/shipping")
def shipping():
    return render_template("shipping.html", title="Доставка и возврат")


@main_bp.route("/contact")
def contact():
    return render_template("contact.html", title="Контакты")


@main_bp.route("/sitemap.xml")
def sitemap():
    """Генерация XML sitemap"""
    pages = []
    base_url = request.url_root.rstrip("/")

    static_routes = [
        {
            "loc": url_for("main.index", _external=True),
            "priority": "1.0",
            "changefreq": "daily",
        },
        {
            "loc": url_for("main.catalog", _external=True),
            "priority": "0.9",
            "changefreq": "daily",
        },
        {
            "loc": url_for("main.about", _external=True),
            "priority": "0.5",
            "changefreq": "monthly",
        },
        {
            "loc": url_for("main.shipping", _external=True),
            "priority": "0.5",
            "changefreq": "monthly",
        },
        {
            "loc": url_for("main.contact", _external=True),
            "priority": "0.5",
            "changefreq": "monthly",
        },
    ]

    pages.extend(static_routes)

    categories = Category.query.all()
    for category in categories:
        pages.append(
            {
                "loc": f"{base_url}{url_for('main.catalog', category_id=category.id)}",
                "priority": "0.8",
                "changefreq": "weekly",
            }
        )

    brands = Brand.query.all()
    for brand in brands:
        pages.append(
            {
                "loc": f"{base_url}{url_for('main.catalog', brand_id=brand.id)}",
                "priority": "0.7",
                "changefreq": "weekly",
            }
        )

    products = Product.query.all()
    for product in products:
        pages.append(
            {
                "loc": f"{base_url}{url_for('main.product', product_id=product.id)}",
                "priority": "0.6",
                "changefreq": "monthly",
                "lastmod": datetime.utcnow().isoformat(),
            }
        )

    sitemap_xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{% for page in pages %}
<url>
    <loc>{{ page.loc }}</loc>
    {% if page.lastmod %}<lastmod>{{ page.lastmod }}</lastmod>{% endif %}
    <changefreq>{{ page.changefreq }}</changefreq>
    <priority>{{ page.priority }}</priority>
</url>
{% endfor %}
</urlset>
    """
    sitemap_xml = render_template_string(sitemap_xml_template, pages=pages)

    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response


# Использование app_errorhandler для регистрации обработчиков на уровне всего приложения
@main_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html", title="Страница не найдена"), 404


@main_bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template("errors/403.html", title="Доступ запрещен"), 403


@main_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("errors/500.html", title="Ошибка сервера"), 500
