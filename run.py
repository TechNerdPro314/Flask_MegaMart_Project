from app import create_app
import os

# Загружаем конфигурацию из переменной окружения FLASK_CONFIG или используем 'default'
config_name = os.getenv("FLASK_CONFIG") or "default"
app = create_app(config_name)

if __name__ == "__main__":
    app.run()
