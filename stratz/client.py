from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_ENDPOINT = "https://api.stratz.com/graphql"
DEFAULT_USER_AGENT = "DraftMind/1.0"
DEFAULT_SECRETS_FILE = "secrets.json"
TOKEN_KEY = "STRATZ_API_TOKEN"


class StratzClient:

    def __init__(
        self,
        token: str | None = None,
        endpoint: str | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.token = token or self._load_token_from_secrets()
        self.endpoint = endpoint or os.getenv("STRATZ_API_URL", DEFAULT_ENDPOINT)
        self.timeout = timeout

        if not self.token:
            raise RuntimeError(
                f"Для рекомендаций нужен токен в {DEFAULT_SECRETS_FILE} (ключ {TOKEN_KEY})."
            )

    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps({
            "query": query,
            "variables": variables or {},
        }).encode("utf-8")

        req = request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "Accept": "application/graphql-response+json, application/json",
                "User-Agent": DEFAULT_USER_AGENT,
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"STRATZ вернул HTTP {exc.code}: {body}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Не удалось подключиться к STRATZ: {exc.reason}"
            ) from exc

        document = json.loads(raw)
        errors = document.get("errors") or []

        if errors:
            messages = "; ".join(
                error.get("message", "Unknown STRATZ error")
                for error in errors
            )
            raise RuntimeError(f"STRATZ GraphQL error: {messages}")

        data = document.get("data")

        if not isinstance(data, dict):
            raise RuntimeError("STRATZ не вернул поле data.")

        return data

    @staticmethod
    def _load_token_from_secrets() -> str | None:
        secrets_path = Path(DEFAULT_SECRETS_FILE)
        if not secrets_path.is_file():
            return None

        try:
            with secrets_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Не удалось прочитать {DEFAULT_SECRETS_FILE}: {exc}"
            ) from exc

        token = payload.get(TOKEN_KEY)
        return token if isinstance(token, str) and token.strip() else None
