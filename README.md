# ЩЕРБИНИНЫ — сайт V3 + API + закрытая панель

## Состав
- `index.html` — главная / executive summary, направления, навигатор
- `services.html` — пять направлений с задачами, диагностикой и форматами результатов
- `approach.html` — методология и этапы
- `cases.html` — шесть **иллюстративных**, не вымышленных клиентских кейсов
- `insights.html` — практические инструменты и чек-листы
- `contact.html` — форма обращения
- `privacy.html` — **заготовка**: требуется утверждённая политика до запуска
- `backend/` — Flask API, SQLite, SMTP, защищённая административная панель
- `DESIGN_SYSTEM.md` — визуальная система

## Важное: GitHub Pages НЕ запускает backend

Рекомендуемая схема:
- GitHub Pages: `https://nikitascherb.github.io/prj_serg/` — публичный сайт.
- Отдельный Python-хостинг с постоянным диском: `https://api.example.com` — сервер Flask.
- Админка: `https://api.example.com/admin/login` (без публичных ссылок на неё).

Адрес админки **не является защитой**. Защита реализована сессионной авторизацией и хешем пароля. Пароль, SMTP и SECRET_KEY задаются только в переменных окружения сервера.

### Сервер
1. Выберите Python-хостинг, поддерживающий постоянное хранилище (volume) и HTTPS. **Эфемерный диск потеряет заявки при перезапуске/редеплое.**
2. Установите зависимости: `pip install -r backend/requirements.txt`.
3. Создайте секрет: `python -c "import secrets; print(secrets.token_hex(32))"`.
4. Создайте хеш админ-пароля: `python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('YOUR_STRONG_PASSWORD'))"`.
5. Заполните переменные окружения по `backend/.env.example`. Не публикуйте `.env` в GitHub. `DATABASE` должен указывать на постоянный диск.
6. Из каталога `backend`: `gunicorn 'app:create_app()' --bind 0.0.0.0:$PORT --workers 1 --threads 4`.
7. Для email заполните `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `NOTIFY_EMAIL`. Используйте отдельный пароль приложения/SMTP-токен, не пароль от почты.
8. Проверьте `https://api.example.com/health` и `https://api.example.com/admin/login`.
9. В корневом `config.js` укажите `apiBase: 'https://api.example.com'`. Если API и сайт на одном домене, оставьте пустую строку.
10. Установите `API_ORIGIN=https://nikitascherb.github.io` для CORS.

### Обработка заявок
- `POST /api/applications` — проверка полей, honeypot, ограничение 5 обращений/IP в час, SQLite, SMTP.
- Успех HTTP 201 означает, что заявка **сохранена в базе**; SMTP-уведомление может отдельно не пройти. В админке виден статус уведомления.
- `/admin/login` — логин/пароль; `/admin` — таблица последних 200 обращений, фильтры; `/admin/applications/<id>` — детали и изменение статуса.
- Включены CSRF-токены для админ-действий, HTTP-only cookies, secure cookies по умолчанию, no-store и X-Frame-Options.
- На локальном HTTP для разработки установите `COOKIE_SECURE=0`; на продакшене — только `1`.
- В качестве следующего уровня безопасности для продакшена рекомендованы резервные копии базы, мониторинг SMTP, WAF/Cloudflare, MFA через внешний identity proxy и отдельные роли пользователей.

### До приёма реальных данных
**Обязательно** заменить `privacy.html` юридически корректной политикой с реквизитами оператора, правилами хранения, передачей данных и порядком отзыва согласия; согласовать SMTP-провайдера и местонахождение базы. Не передавать медицинские и терапевтические сведения через форму.

### Проверки
`python -m compileall backend` и `node --check site.js && node --check app.js`. Интеграционное тестирование SMTP требует реальных настроек и тестового адреса.
