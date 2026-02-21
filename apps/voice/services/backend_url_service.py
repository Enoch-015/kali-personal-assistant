import aiohttp
import logging
from typing import Any, Dict, Optional, Union

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# Header name for ephemeral key authentication (matches Nuxt server)
EPHEMERAL_KEY_HEADER = "x-ephemeral-key"


class BackendURLService:
    """Service to provide the backend URL for LiveKit agents."""

    def __init__(self, settings: Settings = get_settings()):
        self._settings = settings

    @property
    def backend_url(self) -> str:
        """Get the backend URL for LiveKit agents."""
        return self._settings.livekit.backend_url


class BackendRequestService:
    """
    Service for making authenticated requests to the Nuxt backend server.
    
    Uses ephemeral keys for authentication, which are short-lived tokens
    that can be used to authenticate requests from LiveKit agents.
    
    Usage:
        service = BackendRequestService(base_url="https://your-backend.com")
        service.set_ephemeral_key("ek_...")
        
        # Make requests
        config = await service.get("/api/config")
        result = await service.post("/api/livekit/session", {"session_id": "..."})
    """

    def __init__(
        self, 
        base_url: Optional[str] = None,
        ephemeral_key: Optional[str] = None,
        settings: Settings = get_settings(),
        timeout: int = 30,
    ):
        """
        Initialize the backend request service.
        
        Args:
            base_url: The base URL of the backend server. If not provided,
                     uses the backend_url from settings.
            ephemeral_key: The ephemeral key for authentication.
            settings: Application settings instance.
            timeout: Request timeout in seconds.
        """
        self._settings = settings
        self._base_url = base_url or settings.livekit.backend_url
        self._ephemeral_key = ephemeral_key
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def ephemeral_key(self) -> Optional[str]:
        """Get the current ephemeral key."""
        return self._ephemeral_key

    @ephemeral_key.setter
    def ephemeral_key(self, key: Optional[str]) -> None:
        """Set the ephemeral key for authentication."""
        self._ephemeral_key = key

    def set_ephemeral_key(self, key: str) -> "BackendRequestService":
        """
        Set the ephemeral key and return self for chaining.
        
        Args:
            key: The ephemeral key to use for authentication.
            
        Returns:
            Self for method chaining.
        """
        self._ephemeral_key = key
        return self

    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Build request headers including ephemeral key authentication.
        
        Args:
            additional_headers: Additional headers to include.
            
        Returns:
            Dict of headers for the request.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if self._ephemeral_key:
            headers[EPHEMERAL_KEY_HEADER] = self._ephemeral_key
        
        if additional_headers:
            headers.update(additional_headers)
        
        return headers

    def _build_url(self, endpoint: str) -> str:
        """
        Build full URL from endpoint.
        
        Args:
            endpoint: API endpoint (e.g., "/api/config").
            
        Returns:
            Full URL.
        """
        base = self._base_url.rstrip("/")
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{base}{path}"

    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make an authenticated HTTP request to the backend.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH).
            endpoint: API endpoint.
            data: Request body data (for POST, PUT, PATCH).
            params: Query parameters.
            headers: Additional headers.
            
        Returns:
            Response data as dict.
            
        Raises:
            aiohttp.ClientError: On network errors.
            ValueError: On invalid response.
        """
        url = self._build_url(endpoint)
        request_headers = self._get_headers(headers)
        
        logger.debug(f"Making {method} request to {url}")
        
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
            ) as response:
                response_text = await response.text()
                
                if response.status >= 400:
                    logger.error(
                        f"Request failed: {method} {url} - "
                        f"Status: {response.status}, Response: {response_text}"
                    )
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                        message=response_text,
                    )
                
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    # Response is not JSON
                    return {"raw_response": response_text}

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a GET request.
        
        Args:
            endpoint: API endpoint.
            params: Query parameters.
            headers: Additional headers.
            
        Returns:
            Response data.
        """
        return await self.request("GET", endpoint, params=params, headers=headers)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a POST request.
        
        Args:
            endpoint: API endpoint.
            data: Request body data.
            params: Query parameters.
            headers: Additional headers.
            
        Returns:
            Response data.
        """
        return await self.request("POST", endpoint, data=data, params=params, headers=headers)

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a PUT request.
        
        Args:
            endpoint: API endpoint.
            data: Request body data.
            params: Query parameters.
            headers: Additional headers.
            
        Returns:
            Response data.
        """
        return await self.request("PUT", endpoint, data=data, params=params, headers=headers)

    async def patch(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a PATCH request.
        
        Args:
            endpoint: API endpoint.
            data: Request body data.
            params: Query parameters.
            headers: Additional headers.
            
        Returns:
            Response data.
        """
        return await self.request("PATCH", endpoint, data=data, params=params, headers=headers)

    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a DELETE request.
        
        Args:
            endpoint: API endpoint.
            params: Query parameters.
            headers: Additional headers.
            
        Returns:
            Response data.
        """
        return await self.request("DELETE", endpoint, params=params, headers=headers)

    # ============================================================
    # Convenience Methods for Common Endpoints
    # ============================================================

    async def get_org_config(self) -> Dict[str, Any]:
        """
        Get the organization/user configuration.
        
        Returns:
            Configuration data.
        """
        return await self.get("/api/config")

    async def get_livekit_mcp_urls(self, organization_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get MCP server URLs for LiveKit integration.
        
        Args:
            organization_id: Optional organization ID filter.
            
        Returns:
            Dict containing MCP URLs.
        """
        params = {}
        if organization_id:
            params["organization_id"] = organization_id
        return await self.get("/api/mcp", params=params if params else None)

    async def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new LiveKit session.
        
        Args:
            session_data: Session configuration data.
            
        Returns:
            Created session data.
        """
        return await self.post("/api/livekit/session", data=session_data)

    async def update_session(
        self, 
        session_id: str, 
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing LiveKit session.
        
        Args:
            session_id: The session ID to update.
            update_data: Data to update.
            
        Returns:
            Updated session data.
        """
        return await self.patch(f"/api/livekit/session/{session_id}", data=update_data)


# Singleton instance for easy access
_default_service: Optional[BackendRequestService] = None


def get_backend_request_service(
    ephemeral_key: Optional[str] = None,
) -> BackendRequestService:
    """
    Get or create the default backend request service.
    
    Args:
        ephemeral_key: Optional ephemeral key to set.
        
    Returns:
        BackendRequestService instance.
    """
    global _default_service
    
    if _default_service is None:
        _default_service = BackendRequestService()
    
    if ephemeral_key:
        _default_service.set_ephemeral_key(ephemeral_key)
    
    return _default_service