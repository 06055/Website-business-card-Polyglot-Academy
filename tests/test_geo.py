"""Country lookup, proxy trust boundaries and startup without an optional database."""

import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main
import maxminddb
from geo import CountryDetector


class GeoReviewTests(unittest.TestCase):
    def client_ip(self, peer, forwarded, trusted='10.0.0.2/32'):
        detector = CountryDetector(trusted_proxy_cidrs=trusted)
        with main.app.test_request_context('/', environ_base={'REMOTE_ADDR': peer},
                                           headers={'X-Forwarded-For': forwarded}):
            return str(detector.client_ip(main.request))

    def test_only_the_exact_proxy_is_trusted(self):
        self.assertEqual(self.client_ip('10.0.0.3', '8.8.8.8'), '10.0.0.3')
        self.assertEqual(self.client_ip('10.0.0.2', '1.1.1.1, 8.8.8.8'), '8.8.8.8')

    def test_malformed_forwarded_chain_is_rejected(self):
        for header in ('8.8.8.8, invalid', '8.8.8.8,', '', 'unknown', '[2001:4860:4860::8888]:443'):
            with self.subTest(header=header):
                self.assertEqual(self.client_ip('10.0.0.2', header), '10.0.0.2')

    def test_ipv6_and_mapped_ipv4(self):
        self.assertEqual(self.client_ip('::ffff:10.0.0.2', '8.8.8.8'), '8.8.8.8')
        self.assertEqual(self.client_ip('fd00::2', '2001:4860:4860::8888', 'fd00::2/128'),
                         '2001:4860:4860::8888')

    def test_country_database_mapping_and_lookup_cache(self):
        for country, language in (('UA', 'uk'), ('RU', 'ru'), ('DE', 'en'), ('US', 'en'), (None, 'ru')):
            detector = CountryDetector()
            detector._reader_checked = True
            detector._reader = Mock()
            detector._reader.get.return_value = {'country': {'iso_code': country}}
            with self.subTest(country=country), patch.object(main, 'COUNTRY_DETECTOR', detector):
                client = main.app.test_client()
                for route in ('/', '/privacy', '/terms'):
                    response = client.get(route, environ_base={'REMOTE_ADDR': '8.8.8.8'},
                                          headers={'Accept-Language': 'ru-RU'})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers['Content-Language'], language)
                detector._reader.get.assert_called_once_with('8.8.8.8')

    def test_manual_choice_does_not_call_geoip(self):
        client = main.app.test_client()
        client.set_cookie(main.LANGUAGE_COOKIE, 'uk')
        with patch.object(main.COUNTRY_DETECTOR, 'country_for_request', side_effect=AssertionError('GeoIP called')):
            self.assertEqual(client.get('/').headers['Content-Language'], 'uk')

    def test_local_private_and_invalid_ips_use_browser_fallback(self):
        with patch.object(main, 'COUNTRY_DETECTOR', CountryDetector()):
            for peer in ('127.0.0.1', '10.0.0.1', '::1', '::ffff:127.0.0.1', 'invalid'):
                for accept, expected in (('uk-UA', 'uk'), ('ru-RU', 'ru'), ('de-DE', 'en')):
                    with self.subTest(peer=peer, accept=accept):
                        response = main.app.test_client().get('/', environ_base={'REMOTE_ADDR': peer},
                                                              headers={'Accept-Language': accept})
                        self.assertEqual(response.headers['Content-Language'], expected)

    def test_missing_and_corrupt_databases_allow_production_import_and_pages(self):
        # A fresh interpreter imports main:app just as the production WSGI server does.
        code = '''
import json, main
c = main.app.test_client()
responses = [c.get(p, environ_base={'REMOTE_ADDR': '8.8.8.8'},
                   headers={'Accept-Language': 'uk-UA'}) for p in ('/', '/privacy', '/terms', '/health')]
print(json.dumps({'debug': main.app.debug, 'statuses': [r.status_code for r in responses],
                  'language': responses[0].headers['Content-Language']}))
'''
        with tempfile.TemporaryDirectory() as directory:
            corrupt = Path(directory) / 'corrupt.mmdb'
            corrupt.write_bytes(b'not a MaxMind database')
            for path in ('', str(Path(directory) / 'missing.mmdb'), str(corrupt)):
                env = {**os.environ, 'GEOIP_COUNTRY_DB': path, 'TRUSTED_PROXY_CIDRS': ''}
                with self.subTest(path=path):
                    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env,
                                            capture_output=True, text=True, check=True)
                    self.assertEqual(json.loads(result.stdout),
                                     {'debug': False, 'statuses': [200, 200, 200, 200], 'language': 'uk'})

    def test_lookup_errors_and_invalid_records_are_safe(self):
        for value in (None, {}, {'country': None}, {'country': {'iso_code': 42}}, 'invalid',
                      {'country': {'iso_code': 'UKRAINE'}}):
            detector = CountryDetector()
            detector._reader_checked = True
            detector._reader = Mock()
            detector._reader.get.return_value = value
            with self.subTest(value=value):
                self.assertIsNone(detector.country_for_ip(ipaddress.ip_address('8.8.8.8')))
        detector = CountryDetector()
        detector._reader_checked = True
        detector._reader = Mock()
        detector._reader.get.side_effect = maxminddb.errors.InvalidDatabaseError('corrupt')
        self.assertIsNone(detector.country_for_ip(ipaddress.ip_address('8.8.8.8')))


if __name__ == '__main__':
    unittest.main()
