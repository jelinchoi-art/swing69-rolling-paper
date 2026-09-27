from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def list_messages(include_hidden: bool = False) -> list[dict[str, Any]]:
    q = get_client().table("messages").select("*").order("created_at")
    if not include_hidden:
        q = q.eq("is_hidden", False)
    return q.execute().data or []


def add_message(nickname: str, message: str, icon: str) -> dict[str, Any]:
    payload = {
        "nickname": nickname.strip(),
        "message": message.strip(),
        "icon": icon,
    }
    return get_client().table("messages").insert(payload).execute().data[0]


def update_message(message_id: str, **changes: Any) -> None:
    changes["updated_at"] = datetime.now(timezone.utc).isoformat()
    get_client().table("messages").update(changes).eq("id", message_id).execute()


def delete_message(message_id: str) -> None:
    get_client().table("messages").delete().eq("id", message_id).execute()


def reset_layout() -> None:
    get_client().table("messages").update({
        "page": None, "x": None, "y": None, "w": None, "h": None, "font_pt": None
    }).neq("id", "00000000-0000-0000-0000-000000000000").execute()
