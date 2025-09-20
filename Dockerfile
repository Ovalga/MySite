# # Используем официальный образ Python
# FROM python:3.11-slim-buster

# # # Устанавливаем переменные окружения
# # ENV PYTHONDONTWRITEBYTECODE 1
# # ENV PYTHONUNBUFFERED 1

# # Устанавливаем системные зависимости
# RUN apt-get update && apt-get install -y \
#     gcc \
#     libpq-dev \
#     && rm -rf /var/lib/apt/lists/*

# # Устанавливаем рабочую директорию
# WORKDIR /app

# # Копируем и устанавливаем зависимости Python
# COPY requirements.txt /app/
# RUN pip install --no-cache-dir -r requirements.txt

# # Копируем весь проект
# COPY . /app/

# # Собираем статику Django
# RUN python manage.py collectstatic --noinput

# # Команда для запуска приложения
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# 

# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости, включая postgresql-client для pg_isready
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p static

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY wait-for-db.sh /wait-for-db.sh
RUN chmod +x /wait-for-db.sh

RUN mkdir -p staticfiles media

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]