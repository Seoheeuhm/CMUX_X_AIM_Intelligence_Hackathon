import os
import httpx
from base64 import b64encode

TOSS_BASE = "https://api.tosspayments.com/v1"


def _auth_header() -> str:
    secret = os.environ["TOSS_SECRET_KEY"]
    encoded = b64encode(f"{secret}:".encode()).decode()
    return f"Basic {encoded}"


def toss_confirm(payment_key: str, order_id: str, amount: int) -> dict:
    """Toss Payments 결제 승인 API 호출. 실패 시 ValueError 발생."""
    with httpx.Client(timeout=30) as http:
        res = http.post(
            f"{TOSS_BASE}/payments/confirm",
            headers={
                "Authorization": _auth_header(),
                "Content-Type": "application/json",
            },
            json={"paymentKey": payment_key, "orderId": order_id, "amount": amount},
        )
    if res.status_code != 200:
        err = res.json()
        raise ValueError(f"[{err.get('code')}] {err.get('message')}")
    return res.json()
