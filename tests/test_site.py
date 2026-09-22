"""The whole test suite of the business-card site: every page answers and nothing leaks.

    python -m unittest discover -s tests -v
"""
import hashlib
import json
import os
import re
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main  # noqa: E402
from geo import CountryDetector  # noqa: E402
from main import app  # noqa: E402


class PagesTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_every_page_answers(self):
        for path in ('/', '/privacy', '/terms'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn('text/html', response.headers['Content-Type'])
                self.assertGreater(len(response.get_data()), 1000)

    def test_health_is_json_and_cheap(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'ok'})

    def test_static_files_are_served(self):
        for path in ('/static/polyglot_academy_style.css', '/static/images/polyglot-hero-background.png'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()          # a static file response holds an open file handle

    def test_unknown_path_is_404(self):
        self.assertEqual(self.client.get('/no-such-page').status_code, 404)

    def test_debug_is_off_when_imported_by_gunicorn(self):
        # Production imports `app` from main.py; app.run(debug=...) below __main__ never runs.
        self.assertFalse(app.debug)


class BrandAssetsTests(unittest.TestCase):
    """The favicon/logo pack: linked from every page, served, and nothing a page asks for is missing."""
    ICONS = ('favicon.ico', 'favicon-16x16.png', 'favicon-32x32.png', 'apple-touch-icon.png',
             'android-chrome-192x192.png', 'android-chrome-512x512.png', 'site.webmanifest',
             'polyglot-owl-logo.png')
    PAGES = ('/', '/privacy', '/terms')

    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def fetch(self, path):
        response = self.client.get(path)
        body = response.get_data()
        response.close()                  # static responses hold an open file handle
        return response, body

    def local_references(self, html):
        """Every same-site URL a page loads: href, src and each srcset candidate."""
        urls = re.findall(r'(?:href|src)="([^"#]+)"', html)
        for srcset in re.findall(r'srcset="([^"]+)"', html):
            urls += [item.strip().split()[0] for item in srcset.split(',') if item.strip()]
        return {url for url in urls if url.startswith('/') and not url.startswith('//')}

    def test_every_file_of_the_pack_is_served(self):
        for name in self.ICONS:
            with self.subTest(name=name):
                response, body = self.fetch(f'/static/icons/{name}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(body, (ROOT / 'static' / 'icons' / name).read_bytes())

    def test_every_page_links_the_favicon_the_touch_icon_and_the_manifest(self):
        version = main.FAVICON_VERSION
        for page in self.PAGES:
            html = self.fetch(page)[1].decode('utf-8')
            with self.subTest(page=page):
                self.assertIn(f'href="/static/icons/favicon.ico?v={version}"', html)
                self.assertNotIn('favicon.svg', html)
                self.assertIn(f'href="/static/icons/favicon-32x32.png?v={version}"', html)
                self.assertIn(f'href="/static/icons/favicon-16x16.png?v={version}"', html)
                self.assertIn(f'rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon.png?v={version}"', html)
                self.assertIn(f'rel="manifest" href="/static/icons/site.webmanifest?v={version}"', html)

    def test_the_header_shows_the_owl_logo(self):
        html = self.fetch('/')[1].decode('utf-8')
        header = html.split('<header', 1)[1].split('</header>', 1)[0]
        self.assertIn(f'src="/static/icons/polyglot-owl-logo.png?v={main.FAVICON_VERSION}"', header)
        self.assertIn('width="48" height="48"', header, 'no layout shift while the logo loads')
        for gone in ('polyglot_mark.png', 'polyglot-logo.png', 'polyglot-owl-brand.png'):
            self.assertNotIn(gone, header, 'an earlier logo is still in the header')

    def test_the_icons_directory_holds_the_pack_and_nothing_else(self):
        """No leftovers: every file here is linked from a page or the manifest."""
        self.assertEqual(sorted(path.name for path in (ROOT / 'static' / 'icons').iterdir()),
                         sorted(self.ICONS))

    def test_nothing_a_page_loads_is_missing(self):
        for page in self.PAGES:
            for url in sorted(self.local_references(self.fetch(page)[1].decode('utf-8'))):
                with self.subTest(page=page, url=url):
                    self.assertEqual(self.fetch(url)[0].status_code, 200)

    def test_the_manifest_is_valid_and_its_icons_exist_at_their_declared_size(self):
        response, body = self.fetch('/static/icons/site.webmanifest')
        self.assertEqual(response.mimetype, 'application/manifest+json')
        manifest = json.loads(body)
        self.assertEqual(manifest['name'], 'Polyglot Academy')
        self.assertTrue(manifest['icons'])
        for icon in manifest['icons']:
            with self.subTest(icon=icon['src']):
                self.assertIn(f'?v={main.FAVICON_VERSION}', icon['src'])
                response, png = self.fetch(urljoin('/static/icons/site.webmanifest', icon['src']))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
                width, height = struct.unpack('>II', png[16:24])
                self.assertEqual(f'{width}x{height}', icon['sizes'])

    def test_the_root_favicon_is_the_same_icon(self):
        """Browsers and crawlers ask for /favicon.ico whatever the <link> says: never a 404."""
        response, body = self.fetch('/favicon.ico')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'image/vnd.microsoft.icon')
        self.assertEqual(body, (ROOT / 'static' / 'icons' / 'favicon.ico').read_bytes())
        self.assertIn('no-cache', response.headers['Cache-Control'])


class LanguageTests(unittest.TestCase):
    """Language priority: manual cookie, IP country, browser language, then English.

    The server renders it directly, so there is never an English page that turns Ukrainian after loading.
    """
    HEADLINES = {'en': 'Learn a foreign language', 'uk': 'Вивчайте іноземну мову', 'ru': 'Изучайте иностранный язык'}

    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def page(self, path='/', accept=None, cookie=None, country=None):
        if cookie is not None:
            self.client.set_cookie(main.LANGUAGE_COOKIE, cookie)
        headers = {'Accept-Language': accept} if accept is not None else {}
        with patch.object(main.COUNTRY_DETECTOR, 'country_for_request', return_value=country):
            response = self.client.get(path, headers=headers)
        return response, response.get_data(as_text=True)

    def language_of(self, html):
        return re.search(r'<html lang="([a-z]+)"', html).group(1)

    def test_the_browser_language_is_the_fallback_when_country_is_unknown(self):
        for accept, expected in (('uk-UA', 'uk'), ('ru-RU', 'ru'), ('en-US', 'en'), ('de-DE', 'en'), ('pl-PL', 'en')):
            with self.subTest(accept=accept):
                response, html = self.page(accept=accept)
                self.assertEqual(self.language_of(html), expected)
                self.assertEqual(response.headers['Content-Language'], expected)
                self.assertIn(self.HEADLINES[expected], html, 'the text itself is rendered in that language')

    def test_country_decides_the_first_visit(self):
        for country, expected in (('UA', 'uk'), ('RU', 'ru'), ('DE', 'en'), ('US', 'en')):
            with self.subTest(country=country):
                response, html = self.page(country=country, accept='ru-RU')
                self.assertEqual(self.language_of(html), expected)
                self.assertEqual(response.headers['Content-Language'], expected)

    def test_manual_cookie_always_wins_over_country(self):
        for country, cookie, expected in (('UA', 'en', 'en'), ('RU', 'uk', 'uk')):
            with self.subTest(country=country, cookie=cookie):
                client = app.test_client()
                client.set_cookie(main.LANGUAGE_COOKIE, cookie)
                with patch.object(main.COUNTRY_DETECTOR, 'country_for_request', return_value=country):
                    html = client.get('/', headers={'Accept-Language': 'ru-RU'}).get_data(as_text=True)
                self.assertEqual(self.language_of(html), expected)

    def test_detection_rules(self):
        cases = {'uk': 'uk', 'uk-UA,uk;q=0.9,en;q=0.8': 'uk', 'ru': 'ru', 'ru-BY,ru;q=0.9': 'ru', 'ru-KZ': 'ru',
                 'en-GB': 'en', 'de-DE,de;q=0.9': 'en', 'pl-PL,pl;q=0.9,en;q=0.5': 'en', '*': 'en', '': 'en',
                 # the best-rated language wins, whatever the order it is written in
                 'en;q=0.4, uk;q=0.9': 'uk',
                 # the first preference decides: a German browser gets English even if Ukrainian comes second
                 'de-DE,uk;q=0.9': 'en', 'uk;q=0': 'en', 'ru;q=0': 'en'}
        for accept, expected in cases.items():
            with self.subTest(accept=accept):
                self.assertEqual(self.language_of(self.page(accept=accept)[1]), expected)

    def test_a_language_chosen_by_hand_wins_over_the_browser(self):
        for cookie in ('en', 'uk', 'ru'):
            with self.subTest(cookie=cookie):
                self.assertEqual(self.language_of(self.page(accept='de-DE', cookie=cookie)[1]), cookie)
        self.assertEqual(self.language_of(self.page(accept='uk-UA', cookie='en')[1]), 'en')

    def test_an_unknown_saved_value_is_ignored(self):
        self.assertEqual(self.language_of(self.page(accept='de-DE', cookie='fr', country='UA')[1]), 'uk')
        client = app.test_client()
        client.set_cookie(main.LANGUAGE_COOKIE, '%not-a-language')
        with patch.object(main.COUNTRY_DETECTOR, 'country_for_request', return_value=None):
            html = client.get('/', headers={'Accept-Language': 'ru-RU'}).get_data(as_text=True)
        self.assertEqual(self.language_of(html), 'ru')

    def test_the_legal_pages_follow_the_same_rules(self):
        for path, marker in (('/privacy', 'Політика конфіденційності'), ('/terms', 'Користувацька угода')):
            with self.subTest(path=path):
                response, html = self.page(path, accept='uk-UA')
                self.assertEqual(self.language_of(html), 'uk')
                self.assertIn(marker, html)

    def test_caches_keep_the_languages_apart(self):
        response = self.page(accept='uk-UA')[0]
        self.assertIn('Accept-Language', response.headers['Vary'])
        self.assertIn('Cookie', response.headers['Vary'])
        self.assertIn('private', response.headers['Cache-Control'])

    def test_the_page_carries_every_language_for_switching_without_a_reload(self):
        html = self.page(accept='en-US')[1]
        data = json.loads(re.search(r'<script type="application/json" id="i18n-data">(.*?)</script>', html, re.S).group(1))
        self.assertEqual(set(data), {'en', 'uk', 'ru'})
        self.assertEqual(data['uk']['hero_h1'], main.TRANSLATIONS['uk']['home']['hero_h1'])
        self.assertIn('data-lang-cookie="polyglot_lang"', html)

    def test_the_switcher_saves_the_choice_and_never_the_automatic_one(self):
        """static/site.js: only a click writes the cookie; the old localStorage "en" is not a choice."""
        script = (ROOT / 'static' / 'site.js').read_text(encoding='utf-8')
        self.assertIn('Max-Age=31536000; Path=/; SameSite=Lax', script)
        self.assertIn('function chooseLang(lang)', script)
        self.assertIn('saveChoice(lang)', script.split('function chooseLang(lang)', 1)[1].split('}', 1)[0])
        self.assertIn('old === "uk" || old === "ru"', script)
        self.assertNotIn('localStorage.setItem', script)


class CountryDetectorTests(unittest.TestCase):
    def test_untrusted_clients_cannot_spoof_x_forwarded_for(self):
        detector = CountryDetector(trusted_proxy_cidrs='10.0.0.0/8')
        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '203.0.113.10'},
                                      headers={'X-Forwarded-For': '8.8.8.8'}):
            self.assertEqual(str(detector.client_ip(main.request)), '203.0.113.10')

    def test_trusted_proxy_chain_reveals_the_client_from_right_to_left(self):
        detector = CountryDetector(trusted_proxy_cidrs='10.0.0.0/8')
        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '10.0.0.3'},
                                      headers={'X-Forwarded-For': '8.8.8.8, 10.0.0.2'}):
            self.assertEqual(str(detector.client_ip(main.request)), '8.8.8.8')

    def test_local_private_and_missing_database_are_safe_unknowns(self):
        detector = CountryDetector(database_path=ROOT / 'missing.mmdb')
        for value in ('127.0.0.1', '10.0.0.1', 'not-an-ip'):
            with self.subTest(value=value), app.test_request_context('/', environ_base={'REMOTE_ADDR': value}):
                self.assertIsNone(detector.country_for_request(main.request))


class ContentTests(unittest.TestCase):
    """The texts themselves: complete in three languages, no placeholders, the A1-C1 path."""
    LEVELS = ('A1', 'A2', 'B1', 'B2', 'C1')

    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def html(self, path, language):
        self.client.set_cookie(main.LANGUAGE_COOKIE, language)
        return self.client.get(path).get_data(as_text=True)

    def test_every_language_has_every_text(self):
        sections = main.TRANSLATIONS['en'].keys()
        for section in sections:
            keys = {language: set(main.TRANSLATIONS[language][section]) for language in main.LANGUAGES}
            with self.subTest(section=section):
                self.assertEqual(keys['uk'], keys['en'])
                self.assertEqual(keys['ru'], keys['en'])
                for language in main.LANGUAGES:
                    empty = [key for key, text in main.TRANSLATIONS[language][section].items() if not text.strip()]
                    self.assertEqual(empty, [], language)

    def test_every_key_a_template_uses_exists(self):
        for template, section in (('polyglot_academy.html', 'home'), ('privacy.html', 'privacy'),
                                  ('terms.html', 'terms'), ('_legal_top.html', 'common')):
            text = (ROOT / 'templates' / template).read_text(encoding='utf-8')
            keys = set(re.findall(r'data-i18n(?:-html)?="([a-z0-9_]+)"', text))
            keys |= set(re.findall(r'data-i18n-attr="[a-z-]+:([a-z0-9_]+)"', text))
            known = set(main.TRANSLATIONS['en']['common']) | set(main.TRANSLATIONS['en'][section])
            with self.subTest(template=template):
                self.assertTrue(keys)
                self.assertEqual(keys - known, set())

    def test_no_placeholder_or_template_text_reaches_a_visitor(self):
        for language in main.LANGUAGES:
            for path in ('/', '/privacy', '/terms'):
                html = self.html(path, language)
                # the embedded JSON legitimately ends objects with "}}"; the markup must not
                markup = re.sub(r'<script type="application/json" id="i18n-data">.*?</script>', '', html, flags=re.S)
                with self.subTest(language=language, path=path):
                    for placeholder in ('Name Surname', 'insert your link', 'Short description', 'Step #',
                                        't.me/https://', '{{', '}}', '{%'):
                        self.assertNotIn(placeholder, markup)

    def test_the_program_is_a1_to_c1_and_never_beyond(self):
        for language in main.LANGUAGES:
            html = self.html('/', language)
            with self.subTest(language=language):
                codes = re.findall(r'<span class="level__code">([A-C][12])</span>', html)
                self.assertEqual(tuple(codes), self.LEVELS, 'all five levels, in order')
                self.assertIn('A1–C1', html)
                self.assertIn('A1 → C1', html)
                self.assertNotIn('C2', html)
                self.assertNotIn('A1–B2', html)

    def test_each_level_has_a_name_and_a_description_in_every_language(self):
        names = {'en': ('Beginner', 'Elementary', 'Intermediate', 'Upper-Intermediate', 'Advanced'),
                 'uk': ('Початковий', 'Елементарний', 'Середній', 'Вище середнього', 'Просунутий'),
                 'ru': ('Начальный', 'Элементарный', 'Средний', 'Выше среднего', 'Продвинутый')}
        for language, expected in names.items():
            home = main.TRANSLATIONS[language]['home']
            with self.subTest(language=language):
                self.assertEqual(tuple(home[f'level_{code.lower()}_name'] for code in self.LEVELS), expected)
                for code in self.LEVELS:
                    self.assertGreater(len(home[f'level_{code.lower()}_p']), 40)

    def test_no_promise_of_a_result_in_a_number_of_days(self):
        for language in main.LANGUAGES:
            text = json.dumps(main.TRANSLATIONS[language], ensure_ascii=False).lower()
            with self.subTest(language=language):
                self.assertIsNone(re.search(r'\b\d+\s*(days|дн|день|тиж|недел|weeks|місяц|месяц)', text))
                self.assertNotIn('guarantee you', text)

    def test_the_community_is_materials_and_practice_not_news(self):
        expected = {'en': ('materials', 'humor'), 'uk': ('Матеріали', 'гумору'), 'ru': ('Материалы', 'юмора')}
        for language, words in expected.items():
            community = main.TRANSLATIONS[language]['home']['about_card3_p']
            with self.subTest(language=language):
                for word in words:
                    self.assertIn(word, community)
                self.assertNotRegex(community.lower(), r'news|новин|новост')

    def test_every_in_page_link_has_a_target(self):
        html = self.html('/', 'en')
        ids = set(re.findall(r'id="([^"]+)"', html))
        for anchor in set(re.findall(r'href="#([^"]+)"', html)):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, ids)
        for path in ('/privacy', '/terms', '/'):
            self.assertIn(f'href="{path}"', html + self.html('/privacy', 'en'))

    CHANNEL = 'https://t.me/polyglotacademyofficial'
    BOT = 'https://t.me/polyglotacademyofficial_bot'

    def test_the_telegram_links_are_the_real_channel_and_bot(self):
        """Only two Telegram addresses exist on the site, and both are spelled correctly."""
        for path, expected in (('/', {self.CHANNEL, self.BOT}), ('/privacy', {self.CHANNEL}),
                               ('/terms', {self.CHANNEL})):
            for language in ('en', 'uk', 'ru'):
                html = self.html(path, language)
                with self.subTest(path=path, language=language):
                    self.assertEqual(set(re.findall(r'href="(https://t\.me/[^"]*)"', html)), expected)
                    self.assertNotIn('t.me/https', html, 'a link pasted inside a link')

    def test_the_bot_is_offered_once_and_in_every_language(self):
        """The bot belongs in Contacts - one line, not a button repeated in every section."""
        for language in ('en', 'uk', 'ru'):
            html = self.html('/', language)
            with self.subTest(language=language):
                self.assertEqual(html.count(f'href="{self.BOT}"'), 1)
                contacts = html.split('id="contacts"', 1)[1].split('</section>', 1)[0]
                self.assertIn(f'href="{self.BOT}"', contacts)
                self.assertIn('@polyglotacademyofficial_bot', contacts)


class FaviconTests(unittest.TestCase):
    """The icons: the sizes browsers ask for, all of them cut from the one supplied artwork."""
    ICONS = ROOT / 'static' / 'icons'
    # The two artworks delivered by the owner: the shield emblem for the header, the owl's head for
    # the icons. brand/make_icons.py builds everything from them - nothing is drawn by hand.
    # Replacing an artwork means replacing its checksum in the same commit.
    ARTWORK = {'icon_own.png': 'bff0587fde3be4dd70173b5adddee52942d689227bfb48e95c9d4f0a2911be34',
               'own_book.png': 'e0eb0aeddcf75601281cb7a8587b6205f2cb5d7bac8a63db10b15e6713de1e72'}

    def test_the_icons_are_built_from_the_supplied_artwork(self):
        for name, checksum in self.ARTWORK.items():
            source = ROOT / 'brand' / name
            with self.subTest(name=name):
                self.assertTrue(source.is_file(), 'a source of truth for the icons is missing')
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), checksum,
                                 'the artwork changed: rerun brand/make_icons.py and update this checksum')
        self.assertTrue((ROOT / 'brand' / 'make_icons.py').is_file())

    def test_the_png_and_ico_sizes(self):
        for name, size in (('favicon-16x16.png', 16), ('favicon-32x32.png', 32)):
            data = (self.ICONS / name).read_bytes()
            with self.subTest(name=name):
                self.assertEqual(struct.unpack('>II', data[16:24]), (size, size))
        ico = (self.ICONS / 'favicon.ico').read_bytes()
        count = struct.unpack('<H', ico[4:6])[0]
        self.assertEqual(sorted((ico[6 + 16 * i] or 256) for i in range(count)), [16, 32, 48])
        self.assertLess(len(ico), 20_000, 'a favicon, not the full emblem')


class DeploymentFilesTests(unittest.TestCase):
    """The files the VPS needs must exist and stay sane (no Docker on the development machine)."""

    def test_dockerfile_is_production_shaped(self):
        text = (ROOT / 'Dockerfile').read_text(encoding='utf-8')
        self.assertIn('gunicorn', text)
        self.assertIn('USER polyglot', text)
        self.assertIn('HEALTHCHECK', text)
        self.assertNotIn('COPY .env', text)

    def test_dockerignore_and_gitignore_keep_secrets_out(self):
        for name in ('.dockerignore', '.gitignore'):
            with self.subTest(name=name):
                lines = {line.strip() for line in (ROOT / name).read_text(encoding='utf-8').splitlines()}
                self.assertIn('.env', lines)

    def test_env_example_has_no_values_that_look_secret(self):
        for line in (ROOT / '.env.example').read_text(encoding='utf-8').splitlines():
            if line.startswith('#') or '=' not in line:
                continue
            name, value = line.split('=', 1)
            self.assertNotIn('TOKEN', name.upper())
            self.assertLess(len(value.strip()), 20, name)

    def test_requirements_are_pinned(self):
        for line in (ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.startswith('#'):
                self.assertIn('==', line)


if __name__ == '__main__':
    unittest.main()
