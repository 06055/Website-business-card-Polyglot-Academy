"""The whole test suite of the business-card site: every page answers and nothing leaks.

    python -m unittest discover -s tests -v
"""
import json
import os
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
        for path in ('/static/polyglot_academy_style.css', '/static/images/polyglot_mark.png'):
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
             'android-chrome-192x192.png', 'android-chrome-512x512.png', 'site.webmanifest', 'polyglot-logo.png')
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
        for page in self.PAGES:
            html = self.fetch(page)[1].decode('utf-8')
            with self.subTest(page=page):
                self.assertIn('href="/static/icons/favicon.ico"', html)
                self.assertIn('href="/static/icons/favicon-32x32.png"', html)
                self.assertIn('href="/static/icons/favicon-16x16.png"', html)
                self.assertIn('rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon.png"', html)
                self.assertIn('rel="manifest" href="/static/icons/site.webmanifest"', html)

    def test_the_header_shows_the_new_logo(self):
        html = self.fetch('/')[1].decode('utf-8')
        header = html.split('<header', 1)[1].split('</header>', 1)[0]
        self.assertIn('src="/static/icons/polyglot-logo.png"', header)
        self.assertIn('/static/icons/android-chrome-192x192.png 192w', header, 'the light rendition for a 44px slot')
        self.assertIn('width="44" height="44"', header, 'no layout shift while the logo loads')
        self.assertNotIn('polyglot_mark.png', header)

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
                response, png = self.fetch(icon['src'])
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
