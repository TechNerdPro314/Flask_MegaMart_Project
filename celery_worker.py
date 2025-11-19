from app import create_app, celery
import os

config_name = os.getenv("FLASK_CONFIG") or "default"
app = create_app(config_name)
app.app_context().push()
