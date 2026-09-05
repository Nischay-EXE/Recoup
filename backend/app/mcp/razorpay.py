import base64
from typing import Any

from strands.tools.mcp import MCPClient

from app.config import settings


class RazorpayMCPError(RuntimeError):
    """Raised when the Razorpay MCP capability layer fails."""


class RazorpayMCPClient:
    """Capability boundary over Razorpay Remote MCP.

    Only explicitly approved Razorpay capabilities are exposed to the
    recovery engine.
    """

    ALLOWED_TOOLS = {
        "create_payment_link",
        "payment_link_notify",
        "fetch_all_payment_links",
        "fetch_payment_link",
        "fetch_payment",
        "fetch_order",
    }

    def __init__(self) -> None:
        if not settings.razorpay_key_id:
            raise ValueError("RAZORPAY_KEY_ID is not configured.")

        if not settings.razorpay_key_secret:
            raise ValueError("RAZORPAY_KEY_SECRET is not configured.")

        self._client = MCPClient(
            url=settings.razorpay_mcp_url,
            headers={
                "Authorization": self._authorization_header(),
            },
            application_name="revenue-recovery-agent",
            application_version="0.1.0",
        )

        self._tools: dict[str, Any] = {}

    @staticmethod
    def _authorization_header() -> str:
        credentials = (
            f"{settings.razorpay_key_id}:{settings.razorpay_key_secret}"
        )

        encoded = base64.b64encode(
            credentials.encode("utf-8")
        ).decode("ascii")

        return f"Basic {encoded}"

    def connect(self) -> None:
        """Start the MCP connection and load approved capabilities."""
        try:
            self._client.start()

            tools = self._client.list_tools_sync()

            discovered = {
                tool.tool_name: tool
                for tool in tools
            }

            missing = self.ALLOWED_TOOLS - discovered.keys()

            if missing:
                raise RazorpayMCPError(
                    "Required Razorpay MCP tools are unavailable: "
                    + ", ".join(sorted(missing))
                )

            self._tools = {
                name: discovered[name]
                for name in self.ALLOWED_TOOLS
            }

        except RazorpayMCPError:
            raise

        except Exception as exc:
            raise RazorpayMCPError(
                f"Unable to connect to Razorpay MCP: {exc}"
            ) from exc

    def disconnect(self) -> None:
        """Stop the MCP connection."""
        self._client.stop(None, None, None)

    def list_allowed_tools(self) -> list[str]:
        """Return the approved capability names."""
        return sorted(self._tools)

    def get_tool(self, tool_name: str) -> Any:
        """Return one approved MCP capability."""
        if tool_name not in self.ALLOWED_TOOLS:
            raise RazorpayMCPError(
                f"Razorpay MCP tool '{tool_name}' is not allowed "
                "by the recovery capability boundary."
            )

        if tool_name not in self._tools:
            raise RazorpayMCPError(
                "Razorpay MCP client is not connected."
            )

        return self._tools[tool_name]

    def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Invoke one approved Razorpay capability."""
        self.get_tool(tool_name)

        try:
            return self._client.call_tool_sync(
                f"revenue-recovery-{tool_name}",
                tool_name,
                arguments or {},
            )
        except Exception as exc:
            raise RazorpayMCPError(
                f"Razorpay MCP tool '{tool_name}' failed: {exc}"
            ) from exc

    @property
    def client(self) -> MCPClient:
        """Return the underlying Strands MCP client."""
        return self._client
