# Базовый образ Python (легкая версия)
FROM python:3.10-slim

# Настройка, чтобы логи в консоли появлялись мгновенно
ENV PYTHONUNBUFFERED=1

# Создаем папку внутри "виртуального компьютера" Docker
WORKDIR /app

# Копируем список библиотек и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем сам бот
COPY main.py .

# Команда, которая запустится при старте контейнера
CMD ["python", "main.py"]