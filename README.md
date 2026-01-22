Website-business-card-Polyglot-Academy — Landing Page (Ukrainian version below)

Made with HTML / CSS / JavaScript / Flask (Jinja2)
License: MIT

Website-business-card-Polyglot-Academy — це сучасний landing-сайт-візитка для Telegram-каналу та онлайн-школи Polyglot Academy, присвячених вивченню іноземних мов.
Сайт презентує проєкт, формат навчання, відгуки та контакти, а також надає зручний перехід у Telegram.

────────────────────────────────────────────

Опис проєкту

Проєкт реалізований як односторінковий сайт з акцентом на:

просту навігацію

швидкий доступ до ключової інформації

багатомовність

адаптивність для мобільних і десктопних пристроїв

Flask використовується виключно для рендера HTML-шаблонів (Jinja2).
База даних та серверна бізнес-логіка не використовуються.

────────────────────────────────────────────

Основні можливості

• Landing-візитка Telegram-каналу та онлайн-школи
• Три мови інтерфейсу: English / Українська / Русский
• Перемикання мови без перезавантаження сторінки
• Плавний scroll до секцій сайту
• Фіксована верхня панель з динамічною зміною стилю
• Мобільне меню (burger menu)
• Мінімалістичні анімації UI
• Адаптивна верстка

────────────────────────────────────────────

Використані технології

Frontend

HTML5

CSS3

JavaScript (Vanilla JS)

Backend

Python

Flask

Jinja2 (templates rendering)

────────────────────────────────────────────

JavaScript — що реалізовано

Плавна навігація по якорях (scrollIntoView)

Динамічна зміна стилю header при скролі

Мобільне меню (відкриття / закриття / overlay)

Dropdown-меню вибору мови

Повна клієнтська система локалізації (i18n):

словники для EN / UA / RU

заміна тексту, HTML та атрибутів

збереження обраної мови в localStorage

Автоматичне оновлення року в footer

────────────────────────────────────────────

Структура проєкту

Website-business-card-Polyglot-Academy/
├── main.py                # Flask application (Jinja2 rendering)
├── templates/             # HTML templates
│   └── index.html
├── static/
│   ├── css/               # Styles
│   ├── js/                # JavaScript logic
│   └── images/            # Images / icons
└── README.md

────────────────────────────────────────────

Як запустити проєкт локально
1. Встановити Python

https://www.python.org/downloads/

(під час встановлення увімкнути Add Python to PATH)

2. Встановити Flask
pip install flask

3. Запустити сервер
python main.py

4. Відкрити в браузері
http://127.0.0.1:5000


────────────────────────────────────────────

Призначення проєкту

• Публічний landing-сайт
• Представлення Telegram-каналу Polyglot Academy
• Представлення онлайн-школи
• Навчальний та портфоліо-проєкт

────────────────────────────────────────────

Ідеї для подальшого розвитку

• Підключення бази даних
• Адмін-панель для керування контентом
• Форма запису на заняття
• SEO-оптимізація та Open Graph
• Деплой на VPS / Docker
• Analytics (privacy-friendly)

────────────────────────────────────────────

Автор

GitHub: https://github.com/06055

Проєкт створено для реального використання та як частину портфоліо.
Ліцензія MIT — дозволено використання, модифікацію та поширення з вказанням автора.


────────────────────────────────────────────
ENG


Website-business-card-Polyglot-Academy — Landing Page (English version)

Made with HTML / CSS / JavaScript / Flask (Jinja2)
License: MIT

Website-business-card-Polyglot-Academy is a modern one-page landing website for the Polyglot Academy Telegram channel and online language school.
It presents the project, learning format, reviews and contacts, with a direct link to Telegram.

────────────────────────────────────────────

Project description

The project is implemented as a single-page landing with focus on:

clean navigation

fast access to key information

multilingual interface

responsive design

Flask is used only for HTML template rendering (Jinja2).
No database or backend business logic is included.

────────────────────────────────────────────

Key features

• Landing page for Telegram channel & online school
• Three interface languages: EN / UA / RU
• Client-side language switching (no reload)
• Smooth scrolling navigation
• Dynamic sticky header
• Mobile burger menu
• Minimal UI animations
• Fully responsive layout

────────────────────────────────────────────

Technologies

Frontend

HTML5

CSS3

Vanilla JavaScript

Backend

Python

Flask

Jinja2

────────────────────────────────────────────

Project structure

Website-business-card-Polyglot-Academy/
├── main.py                # Flask application (Jinja2 rendering)
├── templates/             # HTML templates
│   └── index.html
├── static/
│   ├── css/               # Styles
│   ├── js/                # JavaScript logic
│   └── images/            # Images / icons
└── README.md

────────────────────────────────────────────

How to run locally
pip install flask
python main.py


Open in browser:

http://127.0.0.1:5000


────────────────────────────────────────────

Purpose

• Public landing website
• Telegram channel promotion
• Online school presentation
• Portfolio & educational project

────────────────────────────────────────────

Author

GitHub: https://github.com/06055

MIT License — free to use, modify and distribute with attribution.





