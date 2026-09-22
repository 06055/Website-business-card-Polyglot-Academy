import datetime
import json
import os
from pathlib import Path

from flask import Flask, jsonify, make_response, render_template, request, send_from_directory

from geo import CountryDetector

app = Flask(__name__)

ROOT = Path(__file__).resolve().parent

# The site's languages. The switcher labels them EN / UA / RU; the codes are the real language tags.
LANGUAGES = ("en", "uk", "ru")
DEFAULT_LANGUAGE = "en"
# Set only when a visitor picks a language by hand (static/site.js); the server reads it first.
LANGUAGE_COOKIE = "polyglot_lang"
# Bumped whenever the icons change: browsers keep a favicon far longer than any other file.
FAVICON_VERSION = "owl-icon-20260922-v7"
LANGUAGE_META = {
    "en": {"label": "EN", "flag": "fi-us", "name": "English"},
    "uk": {"label": "UA", "flag": "fi-ua", "name": "Українська"},
    "ru": {"label": "RU", "flag": "fi-ru", "name": "Русский"},
}


def load_translations():
    """{language: {section: {key: text}}} from translations/<language>.json - the only copy of the texts."""
    return {code: json.loads((ROOT / "translations" / f"{code}.json").read_text(encoding="utf-8"))
            for code in LANGUAGES}


TRANSLATIONS = load_translations()
COUNTRY_DETECTOR = CountryDetector.from_environment()


def detect_language(accept_languages):
    """The visitor's first preferred language decides: uk* -> uk, ru* -> ru, anything else -> en.

    `accept_languages` is werkzeug's parsed Accept-Language (best quality first) or any iterable of
    language tags / (tag, quality) pairs.
    """
    for item in accept_languages:
        if isinstance(item, tuple) and item[1] <= 0:
            continue
        tag = item[0] if isinstance(item, tuple) else item
        primary = str(tag).strip().lower().replace("_", "-").split("-")[0]
        return primary if primary in ("uk", "ru") else DEFAULT_LANGUAGE
    return DEFAULT_LANGUAGE


def choose_language(req):
    """A manual choice, then IP country, then the browser language, then English."""
    chosen = req.cookies.get(LANGUAGE_COOKIE, "")
    if chosen in LANGUAGES:
        return chosen
    country = COUNTRY_DETECTOR.country_for_request(req)
    if country == "UA":
        return "uk"
    if country == "RU":
        return "ru"
    if country:
        return DEFAULT_LANGUAGE
    return detect_language(req.accept_languages)


def texts_for(language, section):
    return {**TRANSLATIONS[language]["common"], **TRANSLATIONS[language][section]}


def render_page(template, section):
    """The page in the visitor's language straight from the server: no flash of another language.

    The same texts for all three languages go along as JSON, so switching by hand needs no reload.
    """
    language = choose_language(request)
    response = make_response(render_template(
        template,
        lang=language,
        t=texts_for(language, section),
        i18n={code: texts_for(code, section) for code in LANGUAGES},
        languages=LANGUAGE_META,
        language_cookie=LANGUAGE_COOKIE,
        favicon_version=FAVICON_VERSION,
        year=datetime.date.today().year,
    ))
    # The same URL answers in different languages: any cache in between must keep them apart.
    response.headers["Vary"] = "Accept-Language, Cookie"
    response.headers["Content-Language"] = language
    # Country is derived from the connection rather than a request header, so shared caches must not
    # reuse one visitor's first-visit language for another visitor.
    response.cache_control.private = True
    return response


@app.route("/")
def main_window():
    return render_page("polyglot_academy.html", "home")


@app.route("/privacy")
def privacy():
    return render_page("privacy.html", "privacy")


@app.route("/terms")
def terms():
    return render_page("terms.html", "terms")


@app.route("/favicon.ico")
def favicon():
    """Browsers and search engines ask for /favicon.ico at the root whatever the <link> says."""
    response = send_from_directory(
        app.static_folder, "icons/favicon.ico", mimetype="image/vnd.microsoft.icon", max_age=0
    )
    response.cache_control.no_cache = True
    return response


@app.route("/health")
def health():
    """Liveness for Docker/Caddy: the process answers. Nothing else to check - the site is stateless."""
    return jsonify(status="ok")


if __name__ == "__main__":
    # Development only. In production gunicorn imports `app` from this module (see Dockerfile).
    app.run(host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "5000")),
            debug=os.environ.get("FLASK_DEBUG", "1") == "1",
            # the texts live in JSON: an edited translation restarts the development server too
            extra_files=[str(path) for path in (ROOT / "translations").glob("*.json")])
