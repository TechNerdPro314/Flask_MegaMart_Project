from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

# Модель Пользователя
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256)) 
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='customer', lazy=True)
    is_admin = db.Column(db.Boolean, default=False) 

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self, expires_sec=1800): 
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None 
        return User.query.get(user_id)
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    def __repr__(self):
        return f"<User {self.email}>"

# Модель Категории
class Category(db.Model):
    __tablename__ = 'category'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __str__(self):
        if self.parent_id:
            parent = Category.query.get(self.parent_id)
            return f"{parent.name} → {self.name}"
        return self.name
    
    def __repr__(self):
        return f"<Category {self.name}>"

# Модель Бренда
class Brand(db.Model):
    __tablename__ = 'brand'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    logo_url = db.Column(db.String(255))
    products = db.relationship('Product', backref='brand', lazy=True)
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f"<Brand {self.name}>"

# МОДЕЛЬ ИЗОБРАЖЕНИЙ ТОВАРА
class ProductImage(db.Model):
    __tablename__ = 'product_image'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    image_url = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Product', backref=db.backref('images', lazy=True, cascade='all, delete-orphan'))

# Модель Продукта
class Product(db.Model):
    __tablename__ = 'product'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False, index=True)
    old_price = db.Column(db.Numeric(10, 2))
    sku = db.Column(db.String(100), unique=True, index=True)
    in_stock = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False, index=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'), nullable=False, index=True)

    __table_args__ = (
        db.Index('idx_product_name', 'name'),
    )
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    def __repr__(self):
        return f"<Product {self.name}>"

# Модель Заказа
class Order(db.Model):
    __tablename__ = 'order'
    
    id = db.Column(db.Integer, primary_key=True)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), default='Pending', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    shipping_address = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    payment_id = db.Column(db.String(100), nullable=True, index=True)
    
    def __str__(self):
        return f"Заказ #{self.id} от {self.created_at.strftime('%d.%m.%Y')}"
    
    def __repr__(self):
        return f"<Order {self.id}>"

# Модель Элементов Заказа
class OrderItem(db.Model):
    __tablename__ = 'order_item'
    
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def __repr__(self):
        return f"<OrderItem {self.id}>"

# МОДЕЛЬ КОРЗИНЫ
class Cart(db.Model):
    __tablename__ = 'cart'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('cart_items', lazy='dynamic', cascade='all, delete-orphan'))
    product = db.relationship('Product', backref=db.backref('cart_items', lazy='dynamic'))
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='unique_user_product'),
    )
    
    def __str__(self):
        return f"{self.product.name} в корзине {self.user.name}"
    
    def __repr__(self):
        return f"<Cart user={self.user_id} product={self.product_id}>"