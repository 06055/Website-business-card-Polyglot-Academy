"""The whole test suite of the business-card site: every page answers and nothing leaks.

    python -m unittest discover -s tests -v
"""
import os
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
