import os
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse as parse_dt
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def get_db() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"],
        )
    return _client


# ── Sessions ──────────────────────────────────────────────────

def session_get(session_id: str) -> dict | None:
    res = get_db().table("sessions").select("data").eq("id", session_id).maybe_single().execute()
    return res.data["data"] if res.data else None


def session_set(session_id: str, data: dict, user_id: str | None = None) -> None:
    get_db().table("sessions").upsert({
        "id": session_id,
        "user_id": user_id,
        "data": data,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()


def session_update(session_id: str, key: str, value) -> None:
    data = session_get(session_id) or {}
    data[key] = value
    session_set(session_id, data)


# ── Profiles ──────────────────────────────────────────────────

def profile_get(user_id: str) -> dict | None:
    res = get_db().table("profiles").select("*").eq("id", user_id).maybe_single().execute()
    return res.data


def profile_can_generate(user_id: str) -> bool:
    profile = profile_get(user_id)
    if not profile:
        return False
    now = datetime.now(timezone.utc)
    if profile["plan"] == "pro":
        expires = profile.get("pro_expires_at")
        if expires and parse_dt(expires) > now:
            reset_at = profile.get("gen_reset_at")
            if reset_at and parse_dt(reset_at) <= now:
                _reset_monthly_count(user_id)
                profile = profile_get(user_id)
            return profile["gen_count"] < profile["gen_limit"]
    return profile["gen_count"] < profile["gen_limit"]


def profile_increment_gen(user_id: str) -> None:
    profile = profile_get(user_id)
    if profile:
        get_db().table("profiles").update({
            "gen_count": profile["gen_count"] + 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", user_id).execute()


def _reset_monthly_count(user_id: str) -> None:
    get_db().table("profiles").update({
        "gen_count": 0,
        "gen_reset_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", user_id).execute()


def profile_upgrade_to_pro(user_id: str) -> None:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=30)
    get_db().table("profiles").update({
        "plan": "pro",
        "gen_limit": 10,
        "gen_count": 0,
        "pro_expires_at": expires.isoformat(),
        "gen_reset_at": expires.isoformat(),
        "updated_at": now.isoformat(),
    }).eq("id", user_id).execute()


# ── Payments ──────────────────────────────────────────────────

def payment_create(user_id: str, order_id: str, amount: int) -> None:
    get_db().table("payments").insert({
        "user_id": user_id,
        "order_id": order_id,
        "amount": amount,
        "status": "pending",
    }).execute()


def payment_get_status(order_id: str) -> str | None:
    res = get_db().table("payments").select("status").eq("order_id", order_id).maybe_single().execute()
    return res.data["status"] if res.data else None


def payment_confirm(order_id: str, payment_key: str) -> None:
    now = datetime.now(timezone.utc)
    get_db().table("payments").update({
        "payment_key": payment_key,
        "status": "confirmed",
        "paid_at": now.isoformat(),
        "pro_expires_at": (now + timedelta(days=30)).isoformat(),
    }).eq("order_id", order_id).execute()


def payment_fail(order_id: str) -> None:
    get_db().table("payments").update({"status": "failed"}).eq("order_id", order_id).execute()
