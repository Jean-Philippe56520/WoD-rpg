from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


DEVICE_REFRESH_TOKEN_KEY = "wod-rpg.supabase.refresh-token"

_BROWSER_STORAGE_JS = r"""
export default function(component) {
    const { data, setStateValue } = component;
    const storageKey = data.storageKey;
    const action = data.action;

    try {
        if (action === "write") {
            const value = data.value ?? "";
            if (value) {
                window.localStorage.setItem(storageKey, value);
            } else {
                window.localStorage.removeItem(storageKey);
            }
            setStateValue("payload", {loaded: true, value: value, error: ""});
            return;
        }

        if (action === "clear") {
            window.localStorage.removeItem(storageKey);
            setStateValue("payload", {loaded: true, value: "", error: ""});
            return;
        }

        const value = window.localStorage.getItem(storageKey) ?? "";
        setStateValue("payload", {loaded: true, value: value, error: ""});
    } catch (error) {
        setStateValue("payload", {
            loaded: true,
            value: "",
            error: String(error?.message ?? error ?? "browser storage unavailable"),
        });
    }
}
"""

_browser_storage_component = st.components.v2.component(
    "wod_browser_session_storage",
    html="<span style='display:none' aria-hidden='true'></span>",
    js=_BROWSER_STORAGE_JS,
)


@dataclass(frozen=True)
class BrowserSessionValue:
    loaded: bool
    value: str = ""
    error: str = ""


def _mount_storage(*, action: str, value: str = "", key: str) -> BrowserSessionValue:
    default_payload = None if action == "read" else {"loaded": True, "value": value, "error": ""}
    result = _browser_storage_component(
        data={
            "storageKey": DEVICE_REFRESH_TOKEN_KEY,
            "action": action,
            "value": value,
        },
        default={"payload": default_payload},
        key=key,
        on_payload_change=lambda: None,
        height=0,
    )
    payload = result.payload
    if not isinstance(payload, dict):
        return BrowserSessionValue(loaded=False)
    return BrowserSessionValue(
        loaded=bool(payload.get("loaded")),
        value=str(payload.get("value") or ""),
        error=str(payload.get("error") or ""),
    )


def read_device_refresh_token() -> BrowserSessionValue:
    """Lit le refresh token de cet appareil sans jamais conserver le mot de passe."""

    return _mount_storage(action="read", key="wod_device_session_reader")


def persist_device_refresh_token(refresh_token: str) -> None:
    if not refresh_token:
        return
    _mount_storage(
        action="write",
        value=refresh_token,
        key="wod_device_session_writer",
    )


def clear_device_refresh_token() -> None:
    _mount_storage(action="clear", key="wod_device_session_clearer")
