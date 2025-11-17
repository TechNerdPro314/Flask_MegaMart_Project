from flask import Blueprint

# ИСПРАВЛЕНО: переименован blueprint во избежание конфликта имен
cart_bp = Blueprint("cart_app", __name__, template_folder="templates")

from . import routes
