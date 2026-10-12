"""Cliente del Gateway; todos los pasos HTTP pasan por su URL pública."""

import httpx


class GatewayClient:
    def __init__(self, base_url: str, timeout: float):
        self.client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout, trust_env=False)

    def close(self):
        self.client.close()

    def request(self, method, path, *, token=None, json=None, headers=None):
        request_headers = dict(headers or {})
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        return self.client.request(method, path, json=json, headers=request_headers)
