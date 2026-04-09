# Деплой Paddle Booking на сервер

## Требования к серверу
- Ubuntu 22.04 / Debian 12
- Python 3.10
- PostgreSQL 15+
- Nginx

---

## 1. Подготовка сервера

```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем нужные пакеты
sudo apt install -y python3.10 python3.10-venv python3.10-dev \
    postgresql postgresql-contrib nginx git

# Проверяем версию Python
python3.10 --version
```

---

## 2. PostgreSQL — создаём базу данных

```bash
# Заходим в PostgreSQL
sudo -u postgres psql

# Создаём пользователя и базу
CREATE USER paddle_user WITH PASSWORD 'придумайте_пароль';
CREATE DATABASE paddle_booking OWNER paddle_user;
GRANT ALL PRIVILEGES ON DATABASE paddle_booking TO paddle_user;
\q
```

---

## 3. Загрузка проекта

```bash
# Клонируем репозиторий (или загружаем файлы)
git clone https://github.com/ВАШ_РЕПОЗИТОРИЙ.git /home/paddle/app
cd /home/paddle/app

# Создаём виртуальное окружение на Python 3.10
python3.10 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Настройка переменных окружения

```bash
# Копируем шаблон
cp .env.example .env

# Редактируем .env
nano .env
```

Заполните в `.env`:
```
SECRET_KEY=сгенерируйте_ключ
DEBUG=False
ALLOWED_HOSTS=ваш-домен.ru,www.ваш-домен.ru
DATABASE_URL=postgres://paddle_user:пароль@localhost:5432/paddle_booking
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=пароль_приложения_gmail
SITE_URL=https://ваш-домен.ru
```

**Генерация SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 5. Применяем миграции и собираем статику

```bash
source venv/bin/activate

# Создаём папку для логов
mkdir -p logs

# Миграции
python manage.py migrate

# Собираем статику
python manage.py collectstatic --no-input
```

---

## 6. Настройка Gunicorn как системного сервиса

```bash
sudo nano /etc/systemd/system/paddle.service
```

Вставьте (замените пути на свои):
```ini
[Unit]
Description=Paddle Booking Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/home/paddle/app
ExecStart=/home/paddle/app/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/paddle.sock \
    --log-file /home/paddle/app/logs/gunicorn.log \
    paddle_booking.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable paddle
sudo systemctl start paddle
sudo systemctl status paddle
```

---

## 7. Настройка Nginx

```bash
sudo nano /etc/nginx/sites-available/paddle
```

Вставьте (замените домен):
```nginx
server {
    listen 80;
    server_name ваш-домен.ru www.ваш-домен.ru;

    client_max_body_size 10M;

    location /static/ {
        alias /home/paddle/app/staticfiles/;
    }

    location /media/ {
        alias /home/paddle/app/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/paddle.sock;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/paddle /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 8. SSL-сертификат (HTTPS) через Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ваш-домен.ru -d www.ваш-домен.ru
```

После этого Certbot сам обновит конфиг Nginx для HTTPS.

---

## 9. Деплой обновлений

```bash
cd /home/paddle/app
git pull

source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input

sudo systemctl restart paddle
```

---

## Деплой на Railway (проще всего)

Railway автоматически определяет Django-проект.

1. Зарегистрируйтесь на [railway.app](https://railway.app)
2. Нажмите **New Project → Deploy from GitHub repo**
3. Выберите ваш репозиторий
4. Добавьте сервис **PostgreSQL** (кнопка Add Service → Database → PostgreSQL)
5. В настройках проекта добавьте переменные окружения из `.env.example`
6. `DATABASE_URL` Railway подставит автоматически из PostgreSQL-сервиса

Всё — Railway сам запустит `gunicorn` через `Procfile`.

---

## Деплой на Render

1. Зарегистрируйтесь на [render.com](https://render.com)
2. **New → Web Service** → подключите GitHub репозиторий
3. Настройки:
   - **Runtime:** Python 3.10
   - **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate`
   - **Start Command:** `gunicorn paddle_booking.wsgi`
4. Добавьте **PostgreSQL** базу через **New → PostgreSQL**
5. Скопируйте `DATABASE_URL` из базы в переменные окружения Web Service

---

## Структура файлов деплоя

```
├── Procfile           # команда запуска для Railway/Render/Heroku
├── runtime.txt        # версия Python (3.10.14)
├── requirements.txt   # зависимости (включая gunicorn, psycopg2, whitenoise)
├── .env.example       # шаблон переменных окружения
└── DEPLOY.md          # эта инструкция
```
