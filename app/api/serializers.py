from flask import url_for, current_app
from marshmallow import Schema, fields, pre_dump

class ProductImageSchema(Schema):
    image_url = fields.Method("get_absolute_image_url")
    sort_order = fields.Int()

    def get_absolute_image_url(self, obj):
        # Генерирует абсолютный URL: http://domain.com/static/images/filename.jpg
        return url_for('static', filename=f'images/{obj.image_url}', _external=True)

class CategorySchema(Schema):
    id = fields.Int()
    name = fields.Str()
    slug = fields.Str()
    parent_id = fields.Int(allow_none=True)

class ProductListSchema(Schema):
    """Облегченная схема для списков товаров"""
    id = fields.Int()
    name = fields.Str()
    slug = fields.Str()
    price = fields.Float()
    old_price = fields.Float(allow_none=True)
    in_stock = fields.Int()
    # Возвращаем только первую картинку или заглушку
    main_image = fields.Method("get_main_image")
    category = fields.Nested(CategorySchema, only=("id", "name"))

    def get_main_image(self, obj):
        # Логика получения главной картинки (аналогично add_first_image_to_products)
        img_filename = "default_product.png"
        if obj.images:
            sorted_images = sorted(obj.images, key=lambda x: x.sort_order)
            img_filename = sorted_images[0].image_url
        
        return url_for('static', filename=f'images/{img_filename}', _external=True)

class ProductDetailSchema(ProductListSchema):
    """Полная схема для карточки товара"""
    description = fields.Str()
    sku = fields.Str()
    brand = fields.Method("get_brand_name")
    images = fields.List(fields.Nested(ProductImageSchema))
    specifications = fields.Dict() # JSON характеристики
    country = fields.Str()
    warranty = fields.Str()

    def get_brand_name(self, obj):
        return obj.brand.name if obj.brand else None

class UserSchema(Schema):
    id = fields.Int()
    email = fields.Str()
    name = fields.Str()
    phone = fields.Str()
    address = fields.Str()