from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, request

try:
    from .jawwal_client import JawwalPayClient
    from .user_store import UserStore
except ImportError:  # Allows: python app.py
    from jawwal_client import JawwalPayClient
    from user_store import UserStore


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", os.getenv("API_TOKEN", "")).strip()
LEGACY_SESSION_FILE = Path(os.getenv("JAWWAL_SESSION_FILE", DATA_DIR / "jawwal_session.json"))

app = Flask(__name__)
user_store = UserStore(DATA_DIR)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def api_response(payload: dict, status: int = 200):
    body = dict(payload)
    if getattr(g, "user_id", None):
        body["user_id"] = g.user_id
    return jsonify(body), status


def _extract_bearer() -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return ""


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _extract_bearer()
        if not ADMIN_TOKEN or token != ADMIN_TOKEN:
            return api_response({"success": False, "error": "Admin unauthorized"}, 401)
        return view(*args, **kwargs)

    return wrapper


def require_user(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _extract_bearer()
        if not token:
            return api_response({"success": False, "error": "Missing Authorization Bearer token"}, 401)

        user = user_store.resolve_api_key(token)
        if not user:
            return api_response({"success": False, "error": "Invalid API key"}, 401)

        g.user = user
        g.user_id = user["user_id"]
        g.client = JawwalPayClient(session_path=user_store.session_path(g.user_id))
        return view(*args, **kwargs)

    return wrapper


def get_payload() -> dict:
    return request.get_json(silent=True) or {}


def save_pending(payment: dict) -> str:
    path = user_store.pending_path(g.user_id)
    payments = read_json(path, {})
    payment_id = str(uuid.uuid4())
    payments[payment_id] = {
        **payment,
        "payment_id": payment_id,
        "user_id": g.user_id,
        "created_at": now_iso(),
    }
    write_json(path, payments)
    return payment_id


def pop_pending(payment_id: str) -> dict | None:
    path = user_store.pending_path(g.user_id)
    payments = read_json(path, {})
    payment = payments.pop(payment_id, None)
    if payment is not None:
        write_json(path, payments)
    return payment


def append_history(record: dict) -> None:
    path = user_store.history_path(g.user_id)
    history = read_json(path, [])
    history.append(record)
    write_json(path, history)


def filter_history(date_from: str | None, date_to: str | None, status: str | None) -> list[dict]:
    history = read_json(user_store.history_path(g.user_id), [])
    filtered = []
    for item in history:
        completed_at = item.get("completed_at") or item.get("created_at") or ""
        if date_from and completed_at < date_from:
            continue
        if date_to and completed_at > date_to:
            continue
        if status and item.get("status") != status:
            continue
        filtered.append(item)
    return filtered


@app.get("/health")
def health():
    return api_response({"success": True, "service": "jawwal-pay-api", "multi_user": True})


@app.post("/api/admin/users")
@require_admin
def create_user():
    payload = get_payload()
    name = (payload.get("name") or "").strip()
    user_id = (payload.get("user_id") or "").strip() or None
    if not name:
        return api_response({"success": False, "error": "name is required"}, 400)
    try:
        user = user_store.create_user(name=name, user_id=user_id)
    except ValueError as exc:
        return api_response({"success": False, "error": str(exc)}, 400)

    return api_response(
        {
            "success": True,
            "message": "User created — save the api_key now, it identifies this account on every request",
            "user": {
                "user_id": user["user_id"],
                "name": user["name"],
                "api_key": user["api_key"],
                "created_at": user["created_at"],
            },
        },
        201,
    )


@app.get("/api/admin/users")
@require_admin
def list_users():
    return api_response({"success": True, "count": len(user_store.list_users()), "users": user_store.list_users()})


@app.get("/api/me")
@require_user
def me():
    status = g.client.status()
    return api_response(
        {
            "success": True,
            "user": {"user_id": g.user_id, "name": g.user.get("name")},
            "jawwal_status": status,
        }
    )


@app.get("/api/auth/status")
@require_user
def auth_status():
    return api_response({"success": True, "status": g.client.status()})


@app.post("/api/auth/login")
@require_user
def login():
    payload = get_payload()
    username = payload.get("username")
    password = payload.get("password")
    force = bool(payload.get("force", False))
    if not username or not password:
        return api_response({"success": False, "error": "username and password are required"}, 400)
    result = g.client.login(username=username, password=password, force=force)
    return api_response(result, 200 if result.get("success") else 400)


@app.post("/api/auth/otp")
@require_user
def otp():
    payload = get_payload()
    code = payload.get("otp") or payload.get("activationCode") or payload.get("code")
    if not code:
        return api_response({"success": False, "error": "otp is required"}, 400)
    result = g.client.validate_otp(str(code))
    return api_response(result, 200 if result.get("success") else 400)


@app.delete("/api/auth/session")
@require_user
def clear_session():
    g.client.clear_session()
    return api_response({"success": True, "message": "session cleared"})


@app.post("/api/payments/request")
@require_user
def request_payment():
    payload = get_payload()
    mobile = payload.get("mobile") or payload.get("customer_mobile")
    amount = payload.get("amount")
    if not mobile or amount is None:
        return api_response({"success": False, "error": "mobile and amount are required"}, 400)

    result = g.client.initiate_receive_payment(mobile=mobile, amount=amount)
    if not result.get("success"):
        return api_response(result, 400)

    payment_id = save_pending(
        {
            "confirm_action": result.get("confirm_action"),
            "confirm_data": result.get("confirm_data"),
            "summary": result.get("summary"),
            "request": {"mobile": mobile, "amount": amount},
        }
    )
    return api_response(
        {
            "success": True,
            "payment_id": payment_id,
            "next_step": "confirm",
            "summary": result.get("summary"),
            "message": result.get("message"),
        }
    )


@app.post("/api/payments/<payment_id>/confirm")
@require_user
def confirm_payment(payment_id: str):
    payload = get_payload()
    code = payload.get("verification_code") or payload.get("code") or payload.get("otp")
    if not code:
        return api_response({"success": False, "error": "verification_code is required"}, 400)

    pending = pop_pending(payment_id)
    if not pending:
        return api_response({"success": False, "error": "payment_id not found or already confirmed"}, 404)

    result = g.client.confirm_receive_payment(str(code), pending.get("confirm_data") or {})
    details = result.get("details") or {}
    record = {
        "payment_id": payment_id,
        "user_id": g.user_id,
        "created_at": pending.get("created_at"),
        "completed_at": now_iso(),
        "request": pending.get("request"),
        "summary": pending.get("summary"),
        "status": "success" if result.get("success") else "failed",
        "success": bool(result.get("success")),
        "message": result.get("message") or result.get("error"),
        "details": details,
    }
    append_history(record)

    return api_response(
        {
            "success": bool(result.get("success")),
            "payment_id": payment_id,
            "message": record["message"],
            "details": details,
            "history_record": record,
        },
        200 if result.get("success") else 400,
    )


@app.get("/api/payments/pending")
@require_user
def pending_payments():
    payments = read_json(user_store.pending_path(g.user_id), {})
    return api_response({"success": True, "count": len(payments), "payments": payments})


@app.get("/api/payments")
@require_user
def payments_history():
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    status = request.args.get("status")
    transactions = filter_history(date_from, date_to, status)
    return api_response(
        {
            "success": True,
            "source": "local_history",
            "filters": {"from": date_from, "to": date_to, "status": status},
            "count": len(transactions),
            "transactions": transactions,
        }
    )


@app.get("/api/payments/portal")
@require_user
def portal_payments():
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    result = g.client.query_portal_transactions(date_from=date_from, date_to=date_to)
    return api_response(result, 200 if result.get("success") else 400)


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "1") == "1",
    )
