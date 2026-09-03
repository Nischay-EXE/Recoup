import base64
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class RazorpayAPIError(RuntimeError):
    """Raised when a Razorpay API request fails."""


class RazorpayClient:
    """Minimal Razorpay REST client for the recovery executor."""

    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(self, key_id: str, key_secret: str, timeout: int = 20) -> None:
        if not key_id:
            raise ValueError("RAZORPAY_KEY_ID is not configured.")
        if not key_secret:
            raise ValueError("RAZORPAY_KEY_SECRET is not configured.")

        self.key_id = key_id
        self.key_secret = key_secret
        self.timeout = timeout

    def _auth_header(self) -> str:
        credentials = f"{self.key_id}:{self.key_secret}".encode("utf-8")
        encoded = base64.b64encode(credentials).decode("ascii")
        return f"Basic {encoded}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.BASE_URL}{path}"

        if params:
            query = urlencode(
                {
                    key: value
                    for key, value in params.items()
                    if value is not None
                }
            )
            if query:
                url = f"{url}?{query}"

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        request = Request(
            url=url,
            data=data,
            method=method.upper(),
            headers={
                "Authorization": self._auth_header(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))

        except HTTPError as exc:
            raw = b""
            try:
                raw = exc.read()
            except Exception:
                pass

            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                payload = {"raw": raw.decode("utf-8", errors="replace")}

            raise RazorpayAPIError(
                f"Razorpay API error HTTP {exc.code}: {payload}"
            ) from exc

        except URLError as exc:
            raise RazorpayAPIError(
                f"Unable to reach Razorpay API: {exc}"
            ) from exc

        except TimeoutError as exc:
            raise RazorpayAPIError(
                "Razorpay API request timed out."
            ) from exc

        except json.JSONDecodeError as exc:
            raise RazorpayAPIError(
                "Razorpay returned invalid JSON."
            ) from exc

    def find_payment_link_by_reference(
        self,
        reference_id: str,
    ) -> dict[str, Any] | None:
        """Return the newest Payment Link for a unique reference_id."""
        response = self._request(
            "GET",
            "/payment_links/",
            params={"reference_id": reference_id},
        )

        links = response.get("payment_links", [])
        if not isinstance(links, list) or not links:
            return None

        valid_links = [link for link in links if isinstance(link, dict)]
        if not valid_links:
            return None

        valid_links.sort(
            key=lambda link: int(link.get("created_at", 0) or 0),
            reverse=True,
        )
        return valid_links[0]

    def create_payment_link(
        self,
        *,
        amount_minor: int,
        currency: str,
        customer_name: str | None,
        customer_email: str | None,
        customer_contact: str | None,
        reference_id: str,
        description: str,
        notes: dict[str, str],
        notify_email: bool = False,
        notify_sms: bool = False,
    ) -> dict[str, Any]:
        if amount_minor <= 0:
            raise ValueError("Payment Link amount must be greater than zero.")

        if len(reference_id) > 40:
            raise ValueError("Payment Link reference_id must be <= 40 characters.")

        customer: dict[str, Any] = {}
        if customer_name:
            customer["name"] = customer_name
        if customer_email:
            customer["email"] = customer_email
        if customer_contact:
            customer["contact"] = customer_contact

        body: dict[str, Any] = {
            "amount": amount_minor,
            "currency": currency.upper(),
            "accept_partial": False,
            "reference_id": reference_id,
            "description": description,
            "reminder_enable": False,
            "notify": {
                "email": notify_email,
                "sms": notify_sms,
            },
            "notes": notes,
        }

        if customer:
            body["customer"] = customer

        return self._request(
            "POST",
            "/payment_links/",
            body=body,
        )

    def notify_payment_link(
        self,
        payment_link_id: str,
        medium: str,
    ) -> dict[str, Any]:
        if medium not in {"email", "sms"}:
            raise ValueError(
                "Razorpay Payment Link notifications support email or sms."
            )

        return self._request(
            "POST",
            f"/payment_links/{payment_link_id}/notify_by/{medium}",
        )
