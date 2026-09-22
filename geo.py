"""Small, local IP-to-country adapter used only for first-visit language choice."""

from functools import lru_cache
import ipaddress
import os
from pathlib import Path

import maxminddb


def _networks(value):
    """Parse an explicit comma-separated allow-list of reverse-proxy networks."""
    parsed = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            parsed.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            continue
    return tuple(parsed)


def _address(value):
    try:
        address = ipaddress.ip_address(value.strip())
        return getattr(address, "ipv4_mapped", None) or address
    except (AttributeError, ValueError):
        return None


class CountryDetector:
    """Resolve a public client IP with an optional local MaxMind-compatible database.

    Forwarded addresses are considered only when the direct peer belongs to an explicitly
    configured trusted proxy network. The lookup is local and cached; no web API is called.
    """

    def __init__(self, database_path=None, trusted_proxy_cidrs=None):
        self.database_path = Path(database_path) if database_path else None
        self.trusted_proxies = _networks(trusted_proxy_cidrs or "")
        self._reader = None
        self._reader_checked = False

    @classmethod
    def from_environment(cls):
        return cls(
            database_path=os.environ.get("GEOIP_COUNTRY_DB"),
            trusted_proxy_cidrs=os.environ.get("TRUSTED_PROXY_CIDRS"),
        )

    def _is_trusted_proxy(self, address):
        return address is not None and any(address in network for network in self.trusted_proxies)

    def client_ip(self, req):
        """Return the first untrusted address from the right side of a trusted proxy chain."""
        direct_peer = _address(req.remote_addr)
        if direct_peer is None or not self._is_trusted_proxy(direct_peer):
            return direct_peer

        forwarded = [_address(item) for item in req.headers.get("X-Forwarded-For", "").split(",")]
        # An invalid hop must not be skipped: doing so could expose a spoofed address to its left.
        if any(item is None for item in forwarded):
            return direct_peer
        chain = forwarded + [direct_peer]
        for address in reversed(chain):
            if not self._is_trusted_proxy(address):
                return address
        return direct_peer

    def _get_reader(self):
        if not self._reader_checked:
            self._reader_checked = True
            try:
                if self.database_path and self.database_path.is_file():
                    self._reader = maxminddb.open_database(str(self.database_path))
            except (OSError, ValueError, maxminddb.errors.InvalidDatabaseError):
                self._reader = None
        return self._reader

    @lru_cache(maxsize=4096)
    def country_for_ip(self, address):
        """Return an ISO country code, or None for private/unknown IPs and unavailable GeoIP."""
        if address is None or not address.is_global:
            return None
        reader = self._get_reader()
        if reader is None:
            return None
        try:
            record = reader.get(str(address)) or {}
            if not isinstance(record, dict) or not isinstance(record.get("country"), dict):
                return None
            code = record.get("country", {}).get("iso_code")
        except (OSError, ValueError, maxminddb.errors.InvalidDatabaseError):
            return None
        return code.upper() if isinstance(code, str) and len(code) == 2 and code.isascii() and code.isalpha() else None

    def country_for_request(self, req):
        return self.country_for_ip(self.client_ip(req))
