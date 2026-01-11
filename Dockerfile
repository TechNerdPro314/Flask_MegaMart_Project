# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в рабочую директорию
COPY . .

# Создаем директорию для логов
RUN mkdir -p logs

# Устанавливаем владельца для файлов
RUN useradd -m appuser && chown -R appuser:appuser /app

# Открываем порт, на котором будет работать приложение
EXPOSE 8000

# Healthcheck для Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Переключаемся на непривилегированного пользователя
USER appuser

# Команда для запуска приложения с использованием gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--keep-alive", "5", "--access-logfile", "-", "--error-logfile", "-", "run:app"]