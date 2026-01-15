from flask import jsonify, request, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User, Product, Category
from app import db
from . import api_bp
from .serializers import ProductListSchema, ProductDetailSchema, UserSchema, CategorySchema
from sqlalchemy.orm import joinedload, selectinload

# --- AUTH ---

@api_bp.route("/auth/login", methods=["POST"])
def mobile_login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    email = request.json.get("email", None)
    password = request.json.get("password", None)

    if not email or not password:
        return jsonify({"msg": "Missing email or password"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "Bad username or password"}), 401

    # Создаем токен. Identity - это ID пользователя (строкой)
    access_token = create_access_token(identity=str(user.id))
    
    # Возвращаем токен и данные пользователя
    user_schema = UserSchema()
    return jsonify({
        "access_token": access_token,
        "user": user_schema.dump(user)
    })

@api_bp.route("/auth/me", methods=["GET"])
@jwt_required()
def mobile_profile():
    # Получаем ID из токена
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    user_schema = UserSchema()
    return jsonify(user_schema.dump(user))

# --- CATALOG ---

@api_bp.route("/mobile/products", methods=["GET"])
def mobile_products_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', type=str)

    query = Product.query.options(
        joinedload(Product.category),
        selectinload(Product.images)
    )

    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    # Пагинация
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    # Сериализация
    schema = ProductListSchema(many=True)
    return jsonify({
        "items": schema.dump(products),
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page
    })

@api_bp.route("/mobile/products/<int:product_id>", methods=["GET"])
def mobile_product_detail(product_id):
    product = Product.query.options(
        joinedload(Product.brand),
        selectinload(Product.images)
    ).get_or_404(product_id)

    schema = ProductDetailSchema()
    return jsonify(schema.dump(product))

@api_bp.route("/mobile/categories", methods=["GET"])
def mobile_categories():
    categories = Category.query.filter_by(parent_id=None).all()
    schema = CategorySchema(many=True)
    return jsonify(schema.dump(categories))