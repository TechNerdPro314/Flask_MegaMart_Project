from flask import current_app as app, render_template, redirect, url_for, flash, request, session, jsonify, make_response
from flask_login import current_user, login_user, logout_user, login_required
from .models import Product, Category, Brand, User, Order, OrderItem, Cart, ProductImage
from app import db, cache, csrf
from datetime import datetime
from .forms import LoginForm, RegisterForm, ProfileForm, ChangePasswordForm
import uuid 
from functools import wraps 
from werkzeug.exceptions import abort
from yookassa import Configuration, Payment

# --- ДЕКОРАТОР: Проверка прав администратора ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Для доступа к админ-панели необходимо войти.', 'warning')
            return redirect(url_for('login', next=url_for('admin.index')))
        
        if not current_user.is_admin:
            flash('Доступ запрещен. Требуются права администратора.', 'danger')
            return redirect(url_for('index'))
            
        return f(*args, **kwargs)
    return decorated_function

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def add_first_image_to_products(products):
    """Добавляет первое изображение к каждому товару в списке"""
    for product in products:
        first_image = ProductImage.query.filter_by(product_id=product.id).order_by(ProductImage.sort_order).first()
        product.first_image = first_image.image_url if first_image else 'default_product.png'
    return products

def get_cart():
    if 'cart' not in session:
        session['cart'] = {}
    return session['cart']

def get_cart_total():
    cart = get_cart()
    total_price = 0
    for item in cart.values():
        total_price += item['price'] * item['quantity']
    return total_price

def get_cart_db():
    """Получить корзину из БД для авторизованного пользователя"""
    if not current_user.is_authenticated:
        return {}
    
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    return {
        str(item.product_id): {
            'id': item.product_id,
            'name': item.product.name,
            'price': float(item.product.price),
            'quantity': item.quantity,
            'image_url': item.product.first_image if hasattr(item.product, 'first_image') else 'default_product.png'
        }
        for item in cart_items
    }

def merge_session_cart_to_db():
    """Перенести корзину из сессии в БД при логине"""
    if 'cart' in session and current_user.is_authenticated:
        session_cart = session['cart']
        for product_id, item in session_cart.items():
            product_id = int(product_id)
            quantity = item['quantity']
            
            cart_item = Cart.query.filter_by(
                user_id=current_user.id, 
                product_id=product_id
            ).first()
            
            if cart_item:
                cart_item.quantity += quantity
            else:
                cart_item = Cart(
                    user_id=current_user.id,
                    product_id=product_id,
                    quantity=quantity
                )
                db.session.add(cart_item)
        
        db.session.commit()
        session.pop('cart', None)

# --- ОБЫЧНЫЕ МАРШРУТЫ ---
@app.route('/')
@app.route('/index')
def index():
    categories = Category.query.order_by(Category.name).limit(6).all() 
    featured_products = Product.query.options(
        db.joinedload(Product.category),
        db.joinedload(Product.brand)
    ).order_by(Product.id.desc()).limit(8).all()
    
    # Добавляем первое изображение к каждому товару
    featured_products = add_first_image_to_products(featured_products)
    
    return render_template(
        'index.html', 
        title='Главная', 
        categories=categories,
        featured_products=featured_products
    )

@app.route('/catalog')
def catalog():
    page = request.args.get('page', 1, type=int)
    per_page = 24

    category_id = request.args.get('category_id', type=int)
    brand_id = request.args.get('brand_id', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    search_query = request.args.get('search_query', type=str)
    sort_by = request.args.get('sort_by', 'price_asc')

    query = Product.query.options(
        db.joinedload(Product.category),
        db.joinedload(Product.brand)
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
        query = query.filter(Product.name.ilike(f'%{search_query}%'))

    if sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'name_asc':
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.price.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    # Добавляем первое изображение к каждому товару
    products = add_first_image_to_products(products)

    all_categories = cache.get('categories')
    if all_categories is None:
        all_categories = Category.query.all()
        cache.set('categories', all_categories, timeout=3600)
    
    all_brands = cache.get('brands')
    if all_brands is None:
        all_brands = Brand.query.all()
        cache.set('brands', all_brands, timeout=3600)

    return render_template(
        'catalog.html',
        title='Каталог',
        products=products,
        pagination=pagination,
        all_categories=all_categories,
        all_brands=all_brands,
        current_category_id=category_id,
        current_brand_id=brand_id,
        current_min_price=min_price,
        current_max_price=max_price,
        current_search_query=search_query,
        current_sort_by=sort_by
    )

@app.route('/product/<int:product_id>')
def product(product_id):
    prod = Product.query.options(
        db.joinedload(Product.category),
        db.joinedload(Product.brand)
    ).get_or_404(product_id)
    
    # Получаем все изображения товара
    images = ProductImage.query.filter_by(product_id=product_id).order_by(ProductImage.sort_order).all()
    
    return render_template('product.html', title=prod.name, product=prod, images=images)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart_product_page(product_id):
    """Добавление товара со страницы продукта (работает для гостей)"""
    product = Product.query.get_or_404(product_id)
    quantity = 1
    
    if request.method == 'POST':
        try:
            quantity = int(request.form.get('quantity', 1))
            if quantity <= 0:
                quantity = 1
        except ValueError:
            quantity = 1
    
    first_image = ProductImage.query.filter_by(product_id=product_id).order_by(ProductImage.sort_order).first()
    image_url = first_image.image_url if first_image else 'default_product.png'
    
    if not current_user.is_authenticated:
        if 'cart' not in session:
            session['cart'] = {}
        
        cart_key = str(product_id)
        if cart_key in session['cart']:
            session['cart'][cart_key]['quantity'] += quantity
        else:
            session['cart'][cart_key] = {
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'quantity': quantity,
                'image_url': image_url
            }
        session.modified = True
        flash(f'"{product.name}" добавлен в корзину', 'success')
        return redirect(request.referrer or url_for('index'))
    
    cart_item = Cart.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)
    
    db.session.commit()
    flash(f'"{product.name}" добавлен в корзину', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if current_user.is_authenticated:
        cart_item = Cart.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
    else:
        cart = get_cart()
        product_key = str(product_id)
        if product_key in cart:
            del cart[product_key]
            session.modified = True
    
    flash('Товар удален из корзины.', 'info')
    return redirect(url_for('cart'))

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    if current_user.is_authenticated:
        cart_item = Cart.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if cart_item:
            quantity = int(request.form.get('quantity', 1))
            if quantity > 0:
                cart_item.quantity = quantity
                db.session.commit()
                flash('Количество обновлено.', 'success')
            else:
                db.session.delete(cart_item)
                db.session.commit()
                flash('Товар удален из корзины.', 'info')
    else:
        cart = get_cart()
        product_key = str(product_id)
        quantity = request.form.get('quantity')
        if product_key in cart and quantity and int(quantity) > 0:
            cart[product_key]['quantity'] = int(quantity)
            session.modified = True
            flash('Количество обновлено.', 'success')
        elif quantity and int(quantity) == 0:
            del cart[product_key]
            session.modified = True
            flash('Товар удален из корзины.', 'info')
    
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if current_user.is_authenticated:
        cart_items = current_user.cart_items.all()
        for item in cart_items:
            first_image = ProductImage.query.filter_by(product_id=item.product_id).order_by(ProductImage.sort_order).first()
            item.product.first_image = first_image.image_url if first_image else 'default_product.png'
        
        total_price = sum(item.product.price * item.quantity for item in cart_items)
        return render_template(
            'cart.html', 
            title='Корзина', 
            cart_items=cart_items, 
            total_price=total_price
        )
    else:
        cart_items = get_cart()
        total_price = get_cart_total()
        return render_template(
            'cart.html', 
            title='Корзина', 
            cart_items=cart_items.values(), 
            total_price=total_price
        )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    
    if form.validate_on_submit():
        new_user = User(
            email=form.email.data,
            name=form.name.data
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        merge_session_cart_to_db()
        flash('Вы успешно зарегистрированы!', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html', title='Регистрация', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный email или пароль', 'danger')
            return redirect(url_for('login'))
            
        login_user(user, remember=form.remember.data)
        merge_session_cart_to_db()
        
        next_page = request.args.get('next')
        
        if user.is_admin:
            flash(f'Добро пожаловать в админ-панель, {user.name}!', 'success')
            return redirect(next_page or url_for('admin.index'))
        
        flash(f'Добро пожаловать, {user.name}!', 'success')
        return redirect(next_page or url_for('index'))
    
    return render_template('login.html', title='Вход', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('profile.html', title='Личный кабинет', orders=orders)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        existing_user = User.query.filter(User.email == form.email.data, User.id != current_user.id).first()
        if existing_user:
            flash('Этот Email уже используется другим пользователем.', 'danger')
            return redirect(url_for('edit_profile'))

        current_user.name = form.name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        current_user.address = form.address.data
        
        try:
            db.session.commit()
            flash('Данные профиля успешно обновлены.', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении профиля: {e}', 'danger')

    return render_template('edit_profile.html', title='Редактировать профиль', form=form)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Неверный текущий пароль.', 'danger')
            return redirect(url_for('change_password'))

        current_user.set_password(form.new_password.data)
        try:
            db.session.commit()
            flash('Пароль успешно изменен.', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при изменении пароля: {e}', 'danger')

    return render_template('change_password.html', title='Изменить пароль', form=form)

@app.route('/order/<int:order_id>')
@login_required
def order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template('order.html', title=f'Заказ №{order.id}', order=order)

@app.route('/pay_order/<int:order_id>')
@login_required
def pay_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    if order.status == 'Paid':
        flash('Этот заказ уже оплачен.', 'warning')
        return redirect(url_for('profile'))

    Configuration.account_id = app.config['YOOKASSA_SHOP_ID']
    Configuration.secret_key = app.config['YOOKASSA_SECRET_KEY']
    
    idempotency_key = str(uuid.uuid4())
    total_price = order.total_amount

    try:
        price_str = f"{total_price:.2f}" 

        payment = Payment.create({
            "amount": {
                "value": price_str, 
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": url_for('order_success', order_id=order.id, _external=True) 
            },
            "capture": True,
            "description": f"Повторная оплата заказа №{order.id} в MegaMart",
            "metadata": {
                "order_id": order.id
            }
        }, idempotency_key)
        
        order.payment_id = payment.id
        db.session.commit()
        
        return redirect(payment.confirmation.confirmation_url)
            
    except Exception as e:
        flash(f"Ошибка при создании платежа: {e}", "danger")
        return redirect(url_for('profile'))

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = user.get_reset_token()
            reset_url = url_for('reset_token', token=token, _external=True)
            app.logger.info("-" * 50)
            app.logger.info(f"СБРОС ПАРОЛЯ ДЛЯ {user.email}. ССЫЛКА: {reset_url}")
            app.logger.info("-" * 50)
            
            flash('На ваш email отправлена инструкция по сбросу пароля (проверьте консоль).', 'info')
        else:
            flash('Пользователь с таким email не найден.', 'danger')
            
        return redirect(url_for('login'))
        
    return render_template('reset_request.html', title='Восстановление пароля')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    user = User.verify_reset_token(token)
    
    if user is None:
        flash('Ссылка для сброса пароля недействительна или срок ее действия истек.', 'danger')
        return redirect(url_for('reset_request'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if password != password_confirm:
            flash('Пароли не совпадают.', 'danger')
            return redirect(url_for('reset_token', token=token))
            
        user.set_password(password)
        db.session.commit()
        flash('Ваш пароль успешно изменен. Можете войти.', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_token.html', title='Установить новый пароль')

@app.route('/admin')
@admin_required 
def admin_redirect():
    return redirect(url_for('admin.index'))

@app.route('/yookassa-webhook', methods=['POST'])
def yookassa_webhook():
    event_json = request.json
    
    Configuration.account_id = app.config['YOOKASSA_SHOP_ID']
    Configuration.secret_key = app.config['YOOKASSA_SECRET_KEY']
    
    try:
        event = event_json.get('event')
        payment = event_json.get('object')
        
        if event == 'payment.succeeded':
            order_id = int(payment['metadata']['order_id'])
            order = Order.query.get(order_id)
            
            if order and order.status != 'Paid':
                order.status = 'Paid'
                db.session.commit()
                
        elif event == 'payment.canceled' or event == 'payment.failed':
            order_id = int(payment['metadata']['order_id'])
            order = Order.query.get(order_id)
            
            if order and order.status != 'Paid':
                order.status = 'Failed'
                db.session.commit()

    except Exception as e:
        app.logger.error(f"Ошибка обработки Webhook YooKassa: {e}")
        return jsonify({"status": "error"}), 500

    return jsonify({"status": "ok"}), 200

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = get_cart_db()
    total_price = sum(item['price'] * item['quantity'] for item in cart.values())

    if not cart:
        flash('Ваша корзина пуста. Нечего оформлять.', 'warning')
        return redirect(url_for('catalog'))

    if request.method == 'POST':
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        if not phone or not address:
            flash('Пожалуйста, укажите телефон и адрес доставки.', 'danger')
            return redirect(url_for('checkout'))
        
        new_order = Order(
            user_id=current_user.id,
            total_amount=total_price,
            shipping_address=address,
            status='Pending'
        )
        db.session.add(new_order)
        db.session.commit()
        
        for item in cart.values():
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item['id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)
            
        current_user.phone = phone
        current_user.address = address
        db.session.commit()

        Configuration.account_id = app.config['YOOKASSA_SHOP_ID']
        Configuration.secret_key = app.config['YOOKASSA_SECRET_KEY']
        
        idempotency_key = str(uuid.uuid4())
        
        try:
            price_str = f"{total_price:.2f}" 

            payment = Payment.create({
                "amount": {
                    "value": price_str, 
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": url_for('order_success', order_id=new_order.id, _external=True) 
                },
                "capture": True,
                "description": f"Заказ №{new_order.id} в MegaMart",
                "metadata": {
                    "order_id": new_order.id
                }
            }, idempotency_key)
            
            new_order.payment_id = payment.id
            db.session.commit()
            
            # Очищаем корзину
            Cart.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
            
            return redirect(payment.confirmation.confirmation_url)
            
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при создании платежа: {e}", "danger")
            return redirect(url_for('checkout'))

    return render_template(
        'checkout.html', 
        title='Оформление заказа', 
        cart_items=cart.values(), 
        total_price=total_price,
        user_phone=current_user.phone,
        user_address=current_user.address
    )

@app.route('/order_success/<int:order_id>')
@login_required
def order_success(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    
    if order.status == 'Paid':
        flash('Ваш заказ успешно оплачен!', 'success')
    elif order.status == 'Failed':
        flash('Ошибка оплаты. Пожалуйста, повторите попытку или свяжитесь с нами.', 'danger')
    else:
        flash('Платеж в обработке. Статус заказа скоро обновится.', 'info')
        
    return render_template('order_success.html', title='Статус заказа', order=order)

@app.route('/about')
def about():
    return render_template('about.html', title='О нас')

@app.route('/shipping')
def shipping():
    return render_template('shipping.html', title='Доставка и возврат')

@app.route('/contact')
def contact():
    return render_template('contact.html', title='Контакты')

@app.route('/sitemap.xml')
def sitemap():
    """Генерация XML sitemap"""
    pages = []
    base_url = request.url_root.rstrip('/')
    
    static_routes = [
        {'loc': url_for('index', _external=True), 'priority': '1.0', 'changefreq': 'daily'},
        {'loc': url_for('catalog', _external=True), 'priority': '0.9', 'changefreq': 'daily'},
        {'loc': url_for('about', _external=True), 'priority': '0.5', 'changefreq': 'monthly'},
        {'loc': url_for('shipping', _external=True), 'priority': '0.5', 'changefreq': 'monthly'},
        {'loc': url_for('contact', _external=True), 'priority': '0.5', 'changefreq': 'monthly'},
    ]
    
    pages.extend(static_routes)
    
    categories = Category.query.all()
    for category in categories:
        pages.append({
            'loc': f"{base_url}{url_for('catalog', category_id=category.id)}",
            'priority': '0.8',
            'changefreq': 'weekly'
        })
    
    brands = Brand.query.all()
    for brand in brands:
        pages.append({
            'loc': f"{base_url}{url_for('catalog', brand_id=brand.id)}",
            'priority': '0.7',
            'changefreq': 'weekly'
        })
    
    products = Product.query.all()
    for product in products:
        pages.append({
            'loc': f"{base_url}{url_for('product', product_id=product.id)}",
            'priority': '0.6',
            'changefreq': 'monthly',
            'lastmod': datetime.utcnow().isoformat()
        })
    
    sitemap_xml = render_template_string("""<?xml version="1.0" encoding="UTF-8"?>
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
    """, pages=pages)
    
    response = make_response(sitemap_xml)
    response.headers['Content-Type'] = 'application/xml'
    return response

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html', title='Страница не найдена'), 404

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html', title='Доступ запрещен'), 403

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback() 
    return render_template('errors/500.html', title='Ошибка сервера'), 500

# --- AJAX API для корзины ---
@app.route('/api/cart/add', methods=['POST'])
@login_required
def api_add_to_cart():
    """AJAX: Добавить товар в корзину"""
    try:
        data = request.get_json()
        product_id = int(data.get('product_id'))
        quantity = int(data.get('quantity', 1))
        
        if quantity <= 0:
            return jsonify({'success': False, 'error': 'Неверное количество'}), 400
        
        product = Product.query.get_or_404(product_id)
        
        if product.in_stock < quantity:
            return jsonify({'success': False, 'error': 'Нет в наличии'}), 400
        
        cart_item = Cart.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id
        ).first()
        
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = Cart(
                user_id=current_user.id,
                product_id=product_id,
                quantity=quantity
            )
            db.session.add(cart_item)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Добавлено: {product.name}',
            'cart_count': sum(item.quantity for item in current_user.cart_items)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cart/remove', methods=['POST'])
@login_required
def api_remove_from_cart():
    """AJAX: Удалить товар из корзины"""
    try:
        data = request.get_json()
        product_id = int(data.get('product_id'))
        
        cart_item = Cart.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'cart_count': sum(item.quantity for item in current_user.cart_items)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cart/update', methods=['POST'])
@login_required
def api_update_cart():
    """AJAX: Обновить количество товара"""
    try:
        data = request.get_json()
        product_id = int(data.get('product_id'))
        quantity = int(data.get('quantity'))
        
        if quantity <= 0:
            return api_remove_from_cart()
        
        product = Product.query.get_or_404(product_id)
        
        if product.in_stock < quantity:
            return jsonify({'success': False, 'error': 'Недостаточно товара'}), 400
        
        cart_item = Cart.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if cart_item:
            cart_item.quantity = quantity
            db.session.commit()
        
        total_price = sum(
            item.product.price * item.quantity 
            for item in current_user.cart_items
        )
        
        return jsonify({
            'success': True,
            'total_price': float(total_price),
            'cart_count': sum(item.quantity for item in current_user.cart_items)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500