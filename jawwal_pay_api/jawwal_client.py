from __future__ import annotations

import json
import platform
import re
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests

try:
    from curl_cffi import requests as curl_requests
except ImportError:  # pragma: no cover - requests fallback is supported.
    curl_requests = None


BASE_URL = "https://business.jawwalpay.ps"
LOGIN_PAGE = "/login/auth"
LOGIN_POST = "/login/authenticate"
TWO_FACTOR_PAGE = "/login/twoFactorAuth"
TWO_FACTOR_POST = "/login/checkTwoFactorAuth"
MERCHANT_PAYMENT_PAGE = "/merchant/requestPaymentServices"
RECEIVE_PAYMENT_PAGE = "/merchant/receivePayment"
RECEIVE_PAYMENT_CONFIRM = "/merchant/confirmReceivePayment/receivePaymentForm"
SAVE_RECEIVE_PAYMENT = "/merchant/saveReceivePayment"
TRANSACTIONS_PAGE = "/merchant/transactionsServices"
SESSION_TTL_HOURS = 24 * 30


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _create_http_session():
    if curl_requests:
        return curl_requests.Session(impersonate="chrome120")
    return requests.Session()


class JawwalPayClient:
    """HTTP client for the Jawwal Pay business portal."""

    def __init__(
        self,
        session_path: str | Path = "data/jawwal_session.json",
        base_url: str = BASE_URL,
    ):
        self.base_url = base_url.rstrip("/")
        self.session_path = Path(session_path)
        self.state: dict = {}
        self.session = _create_http_session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "ar-PS,ar;q=0.9,en;q=0.8",
                "Accept": "text/html,application/json,application/xhtml+xml,*/*;q=0.8",
            }
        )
        self.load_session()

    def url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    @staticmethod
    def normalize_phone(phone: str) -> str:
        normalized = re.sub(r"[\s\-+]", "", str(phone or ""))
        if normalized.startswith("970"):
            normalized = normalized[3:]
        if normalized.startswith("0"):
            normalized = normalized[1:]
        return normalized

    @staticmethod
    def format_customer_mobile(phone: str) -> str:
        normalized = JawwalPayClient.normalize_phone(phone)
        return f"0{normalized}" if normalized and not normalized.startswith("0") else normalized

    @staticmethod
    def build_fingerprint() -> str:
        parts = ["120", "Chrome", platform.system(), platform.release(), "false", "Asia/Gaza", "ar"]
        return "".join(parts).replace(" ", "")

    def get_fingerprint(self) -> str:
        return self.state.get("fingerprint") or self.build_fingerprint()

    def _cookie_dict(self) -> dict:
        if hasattr(self.session.cookies, "get_dict"):
            return self.session.cookies.get_dict()
        return dict(self.session.cookies)

    def _read_session_file(self) -> dict:
        if not self.session_path.exists():
            return {"cookies": [], "state": {}}
        try:
            data = json.loads(self.session_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"cookies": [], "state": {}}
        if isinstance(data, list):
            return {"cookies": data, "state": {}}
        return {"cookies": data.get("cookies", []), "state": data.get("state", {})}

    def load_session(self) -> bool:
        data = self._read_session_file()
        self.session.cookies.clear()
        for cookie in data.get("cookies", []):
            name = cookie.get("name")
            value = cookie.get("value")
            if not name or value is None:
                continue
            domain = cookie.get("domain") or "business.jawwalpay.ps"
            path = cookie.get("path") or "/"
            self.session.cookies.set(name, value, domain=domain, path=path)
            if domain and not domain.startswith("."):
                self.session.cookies.set(name, value, domain=f".{domain}", path=path)
        self.state = data.get("state", {})
        return bool(data.get("cookies"))

    def save_session(self, state_update: dict | None = None) -> None:
        if state_update:
            self.state = {**self.state, **state_update}

        existing = {c.get("name"): c for c in self._read_session_file().get("cookies", []) if c.get("name")}
        cookies = []
        for name, value in self._cookie_dict().items():
            meta = existing.get(name, {})
            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": meta.get("domain") or "business.jawwalpay.ps",
                    "path": meta.get("path") or "/",
                }
            )

        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_path.write_text(
            json.dumps({"cookies": cookies, "state": self.state}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear_session(self) -> None:
        self.session.cookies.clear()
        self.state = {}
        if self.session_path.exists():
            self.session_path.unlink()

    def _request(self, method: str, path: str, **kwargs):
        timeout = kwargs.pop("timeout", 45)
        response = self.session.request(method, self.url(path), timeout=timeout, **kwargs)
        response.raise_for_status()
        if self._cookie_dict() and self._should_persist_cookies(response):
            self.save_session()
        return response

    @staticmethod
    def _parse_forms(html: str) -> list[dict]:
        forms = []
        for match in re.finditer(r"<form(?P<attrs>[^>]*)>(?P<body>.*?)</form>", html or "", re.S | re.I):
            attrs = match.group("attrs")
            block = match.group("body")
            action_match = re.search(r"action\s*=\s*[\"']([^\"']*)[\"']", attrs, re.I)
            method_match = re.search(r"method\s*=\s*[\"']([^\"']*)[\"']", attrs, re.I)
            inputs = []
            for tag in re.findall(r"<input[^>]+>", block, re.I):
                name_match = re.search(r"name=[\"']([^\"']+)[\"']", tag, re.I)
                if not name_match:
                    continue
                type_match = re.search(r"type=[\"']([^\"']+)[\"']", tag, re.I)
                value_match = re.search(r"value=[\"']([^\"']*)[\"']", tag, re.I)
                inputs.append(
                    {
                        "name": unescape(name_match.group(1)),
                        "type": (type_match.group(1) if type_match else "text").lower(),
                        "value": unescape(value_match.group(1)) if value_match else "",
                    }
                )
            forms.append(
                {
                    "action": unescape(action_match.group(1)) if action_match else "",
                    "method": (method_match.group(1) if method_match else "GET").upper(),
                    "inputs": inputs,
                }
            )
        return forms

    @staticmethod
    def _extract_form_values(form: dict) -> dict:
        return {inp["name"]: inp.get("value", "") for inp in form.get("inputs", []) if inp.get("name")}

    @staticmethod
    def _is_auth_wall_url(url: str) -> bool:
        lowered = (url or "").lower()
        return any(marker in lowered for marker in ("/login/auth", "/login/authenticate", "twofactorauth"))

    def _should_persist_cookies(self, response) -> bool:
        if self._is_auth_wall_url(response.url):
            return not self.state.get("authenticated")
        return True

    def _is_authenticated_html(self, html: str, url: str = "") -> bool:
        lowered_url = (url or "").lower()
        if self._is_auth_wall_url(lowered_url):
            return False
        if any(marker in lowered_url for marker in ("/merchant/", "/users/", "/branch/")):
            return True
        lowered = (html or "").lower()
        if "loginform" in lowered and 'name="password"' in lowered:
            return False
        if "twofactorauth" in lowered and 'name="password"' not in lowered:
            return False
        return "requestpaymentservices" in lowered or "receivepayment" in lowered or "admin@" in (html or "")

    def _needs_otp_html(self, html: str, url: str = "") -> bool:
        lowered_url = (url or "").lower()
        lowered = (html or "").lower()
        if "twofactorauth" in lowered_url or "twofactorauth" in lowered:
            return True
        markers = ("otp", "pin", "رمز", "two factor", "twofactor", "verification code")
        return any(marker in lowered for marker in markers) and 'name="password"' not in lowered

    @staticmethod
    def _strip_html(text: str) -> str:
        clean = re.sub(r"<[^>]+>", " ", text or "")
        return re.sub(r"\s+", " ", clean).strip()

    @staticmethod
    def _is_mostly_arabic(text: str) -> bool:
        arabic = sum(1 for ch in text if "\u0600" <= ch <= "\u06FF")
        letters = sum(1 for ch in text if ch.isalpha())
        return letters > 0 and arabic / letters >= 0.4

    def _parse_html_message(self, html: str) -> str | None:
        for pattern in (
            r"alert-danger[^>]*>.*?<button.*?</button>\s*(.*?)\s*<br",
            r"alert-success[^>]*>.*?<button.*?</button>\s*(.*?)\s*<br",
        ):
            match = re.search(pattern, html or "", re.S | re.I)
            if match:
                text = self._strip_html(match.group(1))
                if text:
                    return text
        return None

    def _english_portal_message(self, raw: str | None, fallback: str) -> str:
        if not raw:
            return fallback
        clean = self._strip_html(raw)
        if not clean or self._is_mostly_arabic(clean):
            return fallback
        return clean

    def _session_is_fresh(self) -> bool:
        authenticated_at = self.state.get("authenticated_at")
        if not authenticated_at:
            return bool(self.state.get("authenticated"))
        try:
            at = datetime.fromisoformat(authenticated_at)
            return datetime.now() - at < timedelta(hours=SESSION_TTL_HOURS)
        except ValueError:
            return False

    def _mark_authenticated(self) -> None:
        self.save_session(
            {
                "authenticated": True,
                "otp_pending": False,
                "authenticated_at": _now_iso(),
            }
        )

    def status(self) -> dict:
        self.load_session()
        authenticated = bool(self.state.get("authenticated")) and not self.state.get("otp_pending") and self._session_is_fresh()
        return {
            "authenticated": authenticated,
            "otp_pending": bool(self.state.get("otp_pending")),
            "authenticated_at": self.state.get("authenticated_at"),
            "cookie_names": sorted(self._cookie_dict().keys()),
            "session_file": str(self.session_path),
        }

    def login(self, username: str, password: str, force: bool = False) -> dict:
        self.load_session()
        if not force and self.status()["authenticated"]:
            return {"success": True, "next_step": "done", "message": "Current session is valid"}

        fingerprint = self.get_fingerprint()
        payload = {
            "username": username.strip(),
            "password": password,
            "lang": "ar_PS",
            "fingerprint": fingerprint,
        }
        try:
            self._request("GET", LOGIN_PAGE)
            response = self._request("POST", LOGIN_POST, data=payload, allow_redirects=True)
        except Exception as exc:
            return {"success": False, "error": str(exc), "next_step": "login"}

        otp_required = self._needs_otp_html(response.text, response.url)
        authenticated = self._is_authenticated_html(response.text, response.url) and not otp_required
        login_error = "login_error" in (response.url or "").lower()

        result = {
            "success": authenticated or otp_required,
            "otp_required": otp_required,
            "next_step": "otp" if otp_required else ("done" if authenticated else "login"),
            "request": {"method": "POST", "url": self.url(LOGIN_POST), "path": LOGIN_POST},
            "response": {
                "status_code": response.status_code,
                "final_url": response.url,
                "login_error": login_error,
            },
        }

        if authenticated:
            self._mark_authenticated()
            result["message"] = "Login successful"
            return result

        if otp_required:
            otp_spec = self.discover_otp_request(response.text, response.url)
            otp_spec["method"] = "POST"
            otp_spec["hidden_fields"] = {
                **(otp_spec.get("hidden_fields") or {}),
                "username": username.strip(),
                "fingerprint": fingerprint,
            }
            self.save_session(
                {
                    "otp_pending": True,
                    "authenticated": False,
                    "fingerprint": fingerprint,
                    "otp_request": otp_spec,
                }
            )
            result["otp_request"] = otp_spec
            result["message"] = "OTP sent — enter the code in the next step"
            return result

        result["error"] = "Invalid username or password (portal rejected login)"
        if login_error:
            result["error"] = "Invalid username or password (portal login_error=1)"
        return result

    def discover_otp_request(self, html: str, page_url: str) -> dict:
        forms = self._parse_forms(html)
        otp_form = None
        for form in forms:
            blob = json.dumps(form, ensure_ascii=False).lower()
            if any(token in blob for token in ("otp", "token", "code", "pin", "رمز", "verify")):
                otp_form = form
                break
        if not otp_form and forms:
            otp_form = forms[0]

        action = (otp_form or {}).get("action") or ""
        if not action:
            match = re.search(
                r"function\s+validateActivationCode\s*\(\)\s*\{.*?"
                r"var\s+url\s*=\s*[\"']([^\"']+)[\"']",
                html or "",
                re.S | re.I,
            )
            if match:
                action = match.group(1)
        if action and not action.startswith("http"):
            action = urljoin(page_url, action)
        if not action:
            action = self.url(TWO_FACTOR_POST)

        otp_field = "activationCode"
        hidden_fields = {}
        for inp in (otp_form or {}).get("inputs", []):
            name = inp.get("name")
            if not name:
                continue
            if inp.get("type") == "hidden":
                hidden_fields[name] = inp.get("value", "")
            elif any(token in name.lower() for token in ("otp", "code", "token", "pin", "verify")):
                otp_field = name

        path = re.sub(r"^https?://[^/]+", "", action)
        return {
            "method": "POST",
            "url": action,
            "path": path or TWO_FACTOR_POST,
            "content_type": "application/x-www-form-urlencoded",
            "otp_field": otp_field,
            "hidden_fields": hidden_fields,
        }

    def validate_otp(self, otp: str) -> dict:
        if not self.load_session():
            return {"success": False, "error": "No login session — login first", "next_step": "login"}
        if not self.state.get("otp_pending"):
            return {
                "success": self.status()["authenticated"],
                "message": "No pending OTP",
                "next_step": "done",
            }

        spec = self.state.get("otp_request") or {}
        path = spec.get("path") or TWO_FACTOR_POST
        if path == TWO_FACTOR_PAGE and spec.get("otp_field") == "activationCode":
            path = TWO_FACTOR_POST
        otp_field = spec.get("otp_field") or "activationCode"
        payload = {
            **(spec.get("hidden_fields") or {}),
            otp_field: str(otp).strip(),
            "trustedDevice": "on",
        }

        try:
            response = self.session.request(
                "POST",
                self.url(path),
                data=payload,
                allow_redirects=False,
                timeout=45,
                headers={"Referer": self.url(TWO_FACTOR_PAGE), "X-Requested-With": "XMLHttpRequest"},
            )
            response.raise_for_status()
            self.session.cookies.update(response.cookies)
        except Exception as exc:
            return {"success": False, "error": str(exc), "next_step": "otp"}

        content_type = response.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            try:
                body = response.json()
            except ValueError:
                body = {}
            accepted = bool(body.get("success")) and body.get("showInfo") is not True
            if accepted:
                self.save_session({"otp_pending": False, "trusted_device": True})
                self._warm_authenticated_session()
                self._mark_authenticated()
                return {
                    "success": True,
                    "next_step": "done",
                    "message": "OTP verified and session saved",
                    "response": body,
                    "status": self.status(),
                }
            return {
                "success": False,
                "next_step": "otp",
                "error": self._english_portal_message(body.get("message"), "OTP verification failed"),
                "response": body,
            }

        authenticated = self._is_authenticated_html(response.text, response.url) and not self._needs_otp_html(
            response.text, response.url
        )
        if authenticated:
            self._mark_authenticated()
            return {"success": True, "next_step": "done", "message": "OTP verified and session saved"}
        return {"success": False, "next_step": "otp", "error": "OTP verification failed"}

    def _warm_authenticated_session(self) -> bool:
        for path in ("/", "/merchant/index", MERCHANT_PAYMENT_PAGE, RECEIVE_PAYMENT_PAGE):
            try:
                response = self.session.request(
                    "GET",
                    self.url(path),
                    allow_redirects=True,
                    timeout=45,
                    headers={"Referer": self.url(TWO_FACTOR_PAGE)},
                )
                response.raise_for_status()
                if self._is_authenticated_html(response.text, response.url):
                    self.save_session()
                    return True
            except Exception:
                continue
        return False

    def ensure_authenticated(self) -> dict:
        status = self.status()
        if status["authenticated"]:
            return {"success": True, "status": status}
        if status["otp_pending"]:
            return {"success": False, "next_step": "otp", "error": "OTP required"}
        return {"success": False, "next_step": "login", "error": "Session is not active"}

    def initiate_receive_payment(self, mobile: str, amount) -> dict:
        auth = self.ensure_authenticated()
        if not auth.get("success"):
            return auth

        phone = self.format_customer_mobile(mobile)
        try:
            page = self._request("GET", RECEIVE_PAYMENT_PAGE, allow_redirects=True)
        except Exception as exc:
            return {"success": False, "error": str(exc), "next_step": "login"}
        if not self._is_authenticated_html(page.text, page.url):
            return {"success": False, "error": "Jawwal Pay session is not active", "next_step": "login"}

        forms = self._parse_forms(page.text)
        if not forms:
            return {"success": False, "error": "Could not parse payment request form"}

        form = forms[0]
        payload = {
            **self._extract_form_values(form),
            "amount": str(amount),
            "customerMobileNumber": phone,
            "confirmMobileNumber": phone,
        }
        action = form.get("action") or RECEIVE_PAYMENT_CONFIRM
        try:
            response = self._request(
                "POST",
                action,
                data=payload,
                allow_redirects=True,
                headers={"Referer": self.url(RECEIVE_PAYMENT_PAGE)},
            )
        except Exception as exc:
            return {"success": False, "error": str(exc)}

        if "Request Rejected" in (response.text or ""):
            return {"success": False, "error": "Portal rejected the request"}

        confirm_forms = self._parse_forms(response.text)
        if not confirm_forms:
            return {
                "success": False,
                "error": self._english_portal_message(
                    self._parse_html_message(response.text),
                    "Failed to create payment request",
                ),
            }

        confirm_data = self._extract_form_values(confirm_forms[0])
        return {
            "success": True,
            "next_step": "confirm",
            "confirm_action": confirm_forms[0].get("action") or SAVE_RECEIVE_PAYMENT,
            "confirm_data": confirm_data,
            "summary": {
                "mobile": confirm_data.get("customerMobileNumber") or phone,
                "amount": confirm_data.get("amount") or str(amount),
                "charges": confirm_data.get("charges", "0"),
                "total_amount": confirm_data.get("totalAmount") or str(amount),
                "otp_reference": confirm_data.get("otpReference", ""),
            },
            "message": "Payment request created — enter verification code",
        }

    def confirm_receive_payment(self, verification_code: str, confirm_data: dict) -> dict:
        auth = self.ensure_authenticated()
        if not auth.get("success"):
            return auth

        payload = {**confirm_data, "verificationCode": str(verification_code).strip()}
        try:
            response = self._request(
                "POST",
                SAVE_RECEIVE_PAYMENT,
                data=payload,
                allow_redirects=True,
                headers={"Referer": self.url(RECEIVE_PAYMENT_CONFIRM)},
            )
        except Exception as exc:
            return {"success": False, "error": str(exc)}

        body = response.text or ""
        if "Request Rejected" in body:
            return {"success": False, "error": "Portal rejected the request"}
        if "alert-success" in body:
            details = self._parse_payment_result(body, payload)
            return {
                "success": True,
                "message": details["message"],
                "details": details,
                "response": {"final_url": response.url},
            }

        error = self._english_portal_message(
            self._parse_html_message(body),
            "Payment confirmation failed — check verification code",
        )
        return {
            "success": False,
            "error": error,
            "details": self._payment_result_payload("failed", payload, error),
        }

    def _payment_result_payload(self, status: str, payload: dict, message: str | None = None) -> dict:
        return {
            "status": status,
            "status_label": "success" if status == "success" else "failed",
            "message": message
            or (
                "Payment request sent via SMS successfully"
                if status == "success"
                else "Operation failed"
            ),
            "mobile": payload.get("customerMobileNumber", ""),
            "amount": payload.get("amount", ""),
            "charges": payload.get("charges", "0"),
            "total_amount": payload.get("totalAmount", ""),
            "transaction_type": payload.get("transactionType", ""),
            "otp_reference": payload.get("otpReference", ""),
            "completed_at": _now_iso(),
        }

    def _parse_payment_result(self, html: str, payload: dict) -> dict:
        raw = self._parse_html_message(html)
        message = self._english_portal_message(raw, "Payment request sent via SMS successfully")
        details = self._payment_result_payload("success", payload, message)
        extra_fields = []
        seen = set()
        for pattern in (
            r"<tr[^>]*>\s*<td[^>]*>\s*([^<]+?)\s*</td>\s*<td[^>]*>\s*([^<]+?)\s*</td>\s*</tr>",
            r"<dt[^>]*>\s*([^<]+?)\s*</dt>\s*<dd[^>]*>\s*([^<]+?)\s*</dd>",
        ):
            for raw_label, raw_value in re.findall(pattern, html or "", re.I | re.S):
                label = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", raw_label))).strip(" :")
                value = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", raw_value))).strip()
                if not label or not value or len(label) > 80:
                    continue
                key = (label, value)
                if key in seen:
                    continue
                seen.add(key)
                extra_fields.append({"label": label, "value": value})
        details["extra_fields"] = extra_fields
        return details

    def query_portal_transactions(self, date_from: str | None = None, date_to: str | None = None) -> dict:
        auth = self.ensure_authenticated()
        if not auth.get("success"):
            return auth

        params = {}
        if date_from:
            params.update({"fromDate": date_from, "dateFrom": date_from, "startDate": date_from})
        if date_to:
            params.update({"toDate": date_to, "dateTo": date_to, "endDate": date_to})

        try:
            response = self._request("GET", TRANSACTIONS_PAGE, params=params or None, allow_redirects=True)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

        rows = self._parse_tables(response.text)
        return {
            "success": True,
            "source": "portal",
            "url": response.url,
            "filters": {"from": date_from, "to": date_to},
            "count": len(rows),
            "transactions": rows,
            "note": "Portal report scrape is best-effort; field names may change on Jawwal Pay.",
        }

    @staticmethod
    def _parse_tables(html: str) -> list[dict]:
        rows = []
        for table in re.findall(r"<table[^>]*>(.*?)</table>", html or "", re.S | re.I):
            headers = []
            header_match = re.search(r"<thead[^>]*>(.*?)</thead>", table, re.S | re.I)
            if header_match:
                headers = [
                    re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", cell))).strip()
                    for cell in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", header_match.group(1), re.S | re.I)
                ]
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S | re.I):
                cells = [
                    re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", cell))).strip()
                    for cell in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S | re.I)
                ]
                cells = [cell for cell in cells if cell]
                if not cells or cells == headers:
                    continue
                if headers and len(headers) == len(cells):
                    rows.append(dict(zip(headers, cells)))
                else:
                    rows.append({"columns": cells})
        return rows
