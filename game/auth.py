from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import httpx


DEFAULT_SUPABASE_PUBLISHABLE_KEY = "sb_publishable_MkPhnzsC2Z2Kq5jt_mnUog_Utg-Z9XO"


class AuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuthSession:
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    expires_at: int

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "AuthSession":
        user = payload.get("user") or {}
        user_id = str(user.get("id") or "").strip()
        access_token = str(payload.get("access_token") or "").strip()
        refresh_token = str(payload.get("refresh_token") or "").strip()
        if not user_id or not access_token or not refresh_token:
            raise AuthError("Supabase n'a pas renvoye de session utilisateur complete")
        expires_at = payload.get("expires_at")
        if expires_at is None:
            expires_at = int(time.time()) + int(payload.get("expires_in") or 3600)
        return cls(
            user_id=user_id,
            email=str(user.get("email") or ""),
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=int(expires_at),
        )


class SupabaseAuthClient:
    def __init__(
        self,
        url: str,
        publishable_key: str = DEFAULT_SUPABASE_PUBLISHABLE_KEY,
        *,
        transport: httpx.BaseTransport | None = None,
    ):
        if not url or not publishable_key:
            raise ValueError("Supabase URL and publishable key are required for authentication")
        if not publishable_key.startswith("sb_publishable_") and publishable_key.count(".") != 2:
            raise ValueError("SUPABASE_PUBLISHABLE_KEY is not a valid publishable/anon key")
        self.http = httpx.Client(
            base_url=f"{url.rstrip('/')}/auth/v1",
            headers={
                "apikey": publishable_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=20.0,
            transport=transport,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else None
        try:
            response = self.http.request(method, path, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise AuthError("Service d'authentification Supabase inaccessible") from exc
        if response.is_error:
            message = "Authentification refusee"
            try:
                error = response.json()
                if isinstance(error, dict):
                    message = str(
                        error.get("msg")
                        or error.get("message")
                        or error.get("error_description")
                        or error.get("error")
                        or message
                    )
            except ValueError:
                pass
            raise AuthError(message)
        if not response.content:
            return {}
        data = response.json()
        return data if isinstance(data, dict) else {}

    def sign_up(self, email: str, password: str) -> AuthSession | None:
        email = email.strip().lower()
        if not email or "@" not in email:
            raise ValueError("Adresse email invalide")
        if len(password) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caracteres")
        payload = self._request("POST", "/signup", payload={"email": email, "password": password})
        if payload.get("access_token"):
            return AuthSession.from_payload(payload)
        return None

    def sign_in(self, email: str, password: str) -> AuthSession:
        email = email.strip().lower()
        if not email or not password:
            raise ValueError("Email et mot de passe requis")
        payload = self._request(
            "POST",
            "/token?grant_type=password",
            payload={"email": email, "password": password},
        )
        return AuthSession.from_payload(payload)

    def refresh(self, refresh_token: str) -> AuthSession:
        payload = self._request(
            "POST",
            "/token?grant_type=refresh_token",
            payload={"refresh_token": refresh_token},
        )
        return AuthSession.from_payload(payload)

    def validate(self, session: AuthSession) -> AuthSession:
        current = session
        if session.expires_at <= int(time.time()) + 60:
            current = self.refresh(session.refresh_token)
        user = self._request("GET", "/user", access_token=current.access_token)
        user_id = str(user.get("id") or "")
        if not user_id or user_id != current.user_id:
            raise AuthError("Session utilisateur invalide")
        email = str(user.get("email") or current.email)
        if email != current.email:
            current = AuthSession(
                user_id=current.user_id,
                email=email,
                access_token=current.access_token,
                refresh_token=current.refresh_token,
                expires_at=current.expires_at,
            )
        return current

    def sign_out(self, access_token: str) -> None:
        self._request("POST", "/logout?scope=local", access_token=access_token)
