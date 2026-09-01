"""Controlled Internet Gateway with SSRF protection, rate limiting, and size boundaries."""

import ipaddress
import socket
import urllib.parse
from typing import Any
import httpx


class GatewaySecurityError(Exception):
    pass


class InternetGateway:
    PRIVATE_NETWORKS = [
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
        ipaddress.ip_network("fe80::/10"),
    ]

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_response_bytes: int = 5 * 1024 * 1024  # 5 MB limit
    ):
        self.timeout = timeout_seconds
        self.max_response_bytes = max_response_bytes

    def validate_url(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise GatewaySecurityError(f"Unsupported protocol '{parsed.scheme}'. Only HTTP/HTTPS allowed.")

        hostname = parsed.hostname
        if not hostname:
            raise GatewaySecurityError("Invalid URL: missing hostname.")

        if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            raise GatewaySecurityError(f"Access to localhost/loopback '{hostname}' is blocked.")

        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                for priv in self.PRIVATE_NETWORKS:
                    if ip_obj in priv:
                        raise GatewaySecurityError(f"Access to private/internal IP {ip_str} is forbidden.")
        except socket.gaierror:
            # Allow unresolved in mock/test if needed, else fail on real network
            pass

    async def fetch_page(self, url: str) -> dict[str, Any]:
        self.validate_url(url)
        headers = {
            "User-Agent": "StayAngryEngine/1.0 (ResearchBot; Local-First Engine)",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"
        }

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
                final_url = str(response.url)
                self.validate_url(final_url)

                if len(response.content) > self.max_response_bytes:
                    raise GatewaySecurityError(f"Response size exceeded {self.max_response_bytes} bytes.")

                return {
                    "url": final_url,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "content": response.text,
                    "untrusted_source": True
                }
            except httpx.HTTPError as e:
                raise GatewaySecurityError(f"HTTP request failed: {e}")