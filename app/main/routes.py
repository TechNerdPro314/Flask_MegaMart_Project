from flask import (
    render_template,
    request,
    url_for,
    make_response,
    current_app,
    render_template_string,
    session,
    redirect,
    flash,
    send_from_directory,
)
from flask_login import current_user, login_required
from app import db, cache
from app.models import Product, Category, Brand, ProductImage, Review, Order, User
from app.forms import ReviewForm
from datetime import datetime
from . import main_bp
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import func
import os


def add_first_image_to_products(products):
    """
    Эффективно добавляет первое изображение к каждому товару в списке.
    Предполагается, что `product.images` уже загружены с помощью selectinload.
    """
    for product in products:
        if product.images:
            # Сортируем уже загруженные изображения по sort_order
            sorted_images = sorted(product.images, key=lambda img: img.sort_order)
            product.first_image = sorted_images[0].image_url
        else:
            product.first_image = "default_product.png"
    return products


@main_bp.route("/")
@main_bp.route("/index")
def index():
    categories = Category.query.order_by(Category.name).limit(6).all()
    featured_products_query = Product.query.options(
        joinedload(Product.category),
        joinedload(Product.brand),
        selectinload(Product.images),
    )
    featured_products = (
        featured_products_query.order_by(Product.id.desc()).limit(8).all()
    )
    featured_products = add_first_image_to_products(featured_products)
    return render_template(
        "index.html",
        title="Главная",
        categories=categories,
        featured_products=featured_products,
    )


@main_bp.route("/catalog/")
@main_bp.route("/catalog/<slug>")
@cache.cached(
    timeout=300, query_string=True, unless=lambda: current_user.is_authenticated
)
def catalog(slug=None):
    page = request.args.get("page", 1, type=int)
    per_page = 24
    query = Product.query.options(
        joinedload(Product.category),
        joinedload(Product.brand),
        selectinload(Product.images),
    )

    current_category = None
    if slug:
        current_category = Category.query.filter_by(slug=slug).first_or_404()
        query = query.filter(Product.category_id == current_category.id)

    search_query = request.args.get("search_query", type=str)
    brand_id = request.args.get("brand_id", type=int)
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort_by = request.args.get("sort_by", "price_asc")

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

    title = (
        current_category.meta_title
        if current_category and current_category.meta_title
        else (current_category.name if current_category else "Каталог")
    )
    meta_description = (
        current_category.meta_description
        if current_category and current_category.meta_description
        else "Широкий выбор сантехники в нашем каталоге."
    )

    return render_template(
        "catalog.html",
        title=title,
        meta_description=meta_description,
        products=products,
        pagination=pagination,
        all_categories=all_categories,
        all_brands=all_brands,
        current_category=current_category,
        current_brand_id=brand_id,
        current_min_price=min_price,
        current_max_price=max_price,
        current_search_query=search_query,
        current_sort_by=sort_by,
    )


@main_bp.route("/product/<slug>")
@main_bp.route("/product/id/<int:product_id>")
def product(slug=None, product_id=None):
    if slug:
        prod = (
            Product.query.filter_by(slug=slug)
            .options(joinedload(Product.category), joinedload(Product.brand))
            .first_or_404()
        )
    elif product_id:
        prod = (
            Product.query.filter_by(id=product_id)
            .options(joinedload(Product.category), joinedload(Product.brand))
            .first_or_404()
        )
    else:
        abort(404)
    images = (
        ProductImage.query.filter_by(product_id=prod.id)
        .order_by(ProductImage.sort_order)
        .all()
    )

    if "viewed_products" not in session:
        session["viewed_products"] = []
    viewed = session["viewed_products"]
    if prod.id in viewed:
        viewed.remove(prod.id)
    viewed.insert(0, prod.id)
    if len(viewed) > 5:
        viewed.pop()
    session.modified = True

    review_form = ReviewForm()
    reviews = (
        prod.reviews.options(joinedload(Review.author))
        .order_by(Review.created_at.desc())
        .all()
    )
    avg_rating = (
        db.session.query(func.avg(Review.rating))
        .filter(Review.product_id == prod.id)
        .scalar()
        or 0
    )
    avg_rating = round(avg_rating, 1)

    related_products = (
        Product.query.options(selectinload(Product.images))
        .filter(Product.category_id == prod.category_id, Product.id != prod.id)
        .limit(4)
        .all()
    )
    related_products = add_first_image_to_products(related_products)

    return render_template(
        "product.html",
        title=prod.meta_title or prod.name,
        meta_description=prod.meta_description,
        product=prod,
        images=images,
        review_form=review_form,
        reviews=reviews,
        avg_rating=avg_rating,
        related_products=related_products,
    )


@main_bp.route("/product/<slug>/add_review", methods=["POST"])
@main_bp.route("/product/id/<int:product_id>/add_review", methods=["POST"])
@login_required
def add_review(slug=None, product_id=None):
    if slug:
        product = Product.query.filter_by(slug=slug).first_or_404()
    elif product_id:
        product = Product.query.get_or_404(product_id)
    else:
        abort(404)
    form = ReviewForm()
    if form.validate_on_submit():
        existing_review = Review.query.filter_by(
            user_id=current_user.id, product_id=product.id
        ).first()
        if existing_review:
            flash("Вы уже оставляли отзыв на этот товар.", "warning")
            return redirect(url_for("main.product", slug=product.slug))
        review = Review(
            rating=form.rating.data,
            comment=form.comment.data,
            author=current_user,
            product=product,
        )
        db.session.add(review)
        db.session.commit()
        cache.delete_memoized(product, slug=product.slug)
        flash("Спасибо за ваш отзыв!", "success")
        return redirect(url_for("main.product", slug=product.slug))

    images = (
        ProductImage.query.filter_by(product_id=product_id)
        .order_by(ProductImage.sort_order)
        .all()
    )
    reviews = product.reviews.order_by(Review.created_at.desc()).all()
    avg_rating = (
        db.session.query(func.avg(Review.rating))
        .filter(Review.product_id == product_id)
        .scalar()
        or 0
    )
    avg_rating = round(avg_rating, 1)
    related_products = (
        Product.query.options(selectinload(Product.images))
        .filter(Product.category_id == product.category_id, Product.id != product.id)
        .limit(4)
        .all()
    )
    related_products = add_first_image_to_products(related_products)

    return render_template(
        "product.html",
        title=product.name,
        product=product,
        images=images,
        review_form=form,
        reviews=reviews,
        avg_rating=avg_rating,
        related_products=related_products,
    )


@main_bp.route("/about")
def about():
    return render_template("about.html", title="О нас")


@main_bp.route("/shipping")
def shipping():
    return render_template("shipping.html", title="Доставка и возврат")


@main_bp.route("/contact")
def contact():
    return render_template("contact.html", title="Контакты")


@main_bp.route("/sw.js")
def service_worker():
    return send_from_directory(os.path.join(main_bp.static_folder), "js/sw.js")


@main_bp.route("/track_order", methods=["GET", "POST"])
def track_order():
    found_order = None
    if request.method == "POST":
        order_id = request.form.get("order_id")
        email = request.form.get("email")
        if not order_id or not email:
            flash("Пожалуйста, заполните все поля.", "warning")
            return redirect(url_for(".track_order"))
        try:
            order_id_int = int(order_id)
            found_order = (
                Order.query.join(Order.customer)
                .filter(Order.id == order_id_int, User.email == email)
                .first()
            )
            if not found_order:
                flash("Заказ с таким номером и email не найден.", "danger")
        except ValueError:
            flash("Некорректный номер заказа.", "danger")
    return render_template(
        "track_order.html", title="Отследить заказ", order=found_order
    )


@main_bp.route("/sitemap.xml")
def sitemap():
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
                "loc": url_for("main.catalog", slug=category.slug, _external=True),
                "priority": "0.8",
                "changefreq": "weekly",
            }
        )
    products = Product.query.all()
    for product in products:
        pages.append(
            {
                "loc": url_for("main.product", slug=product.slug, _external=True),
                "priority": "0.6",
                "changefreq": "monthly",
                "lastmod": datetime.utcnow().isoformat(),
            }
        )

    sitemap_xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{% for page in pages %}<url>
    <loc>{{ page.loc }}</loc>
    {% if page.lastmod %}<lastmod>{{ page.lastmod }}</lastmod>{% endif %}
    <changefreq>{{ page.changefreq }}</changefreq>
    <priority>{{ page.priority }}</priority>
</url>{% endfor %}
</urlset>"""
    sitemap_xml = render_template_string(sitemap_xml_template, pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@main_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html", title="Страница не найдена"), 404


@main_bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template("errors/403.html", title="Доступ запрещен"), 403


@main_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    current_app.logger.error(f"Server Error: {error}", exc_info=True)
    return render_template("errors/500.html", title="Ошибка сервера"), 500
