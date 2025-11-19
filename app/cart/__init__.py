from flask import Blueprint

# ИСПРАВЛЕНО: __init__ на __name__
cart_app = Blueprint("cart_app", __name__, template_folder="templates")

from . import routes
