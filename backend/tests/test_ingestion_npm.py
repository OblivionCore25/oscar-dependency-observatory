import pytest
import respx
import httpx
from app.ingestion.npm import NpmConnector, PackageNotFoundError, RegistryConnectionError

@pytest.mark.asyncio
async def test_fetch_package_success():
    """Test successful package fetch from npm registry."""
    mock_response = {
        "name": "react",
        "description": "React is a JavaScript library for building user interfaces."
    }
    
    with respx.mock(assert_all_called=True) as mock_respx:
        # Mock the npm registry response
        mock_route = mock_respx.get("https://registry.npmjs.org/react").respond(
            status_code=200, json=mock_response
        )
        
        async with NpmConnector() as connector:
            data = await connector.fetch_package("react")
            
        assert data == mock_response
        assert mock_route.called


@pytest.mark.asyncio
async def test_fetch_scoped_package_success():
    """Test successful fetch for scoped packages (@scope/pkg)."""
    mock_response = {"name": "@types/node"}
    
    with respx.mock(assert_all_called=True) as mock_respx:
        # urllib.parse.quote will keep @ and / safe if configured that way, 
        # or it will encode them. The NpmConnector uses safe='@/'
        mock_route = mock_respx.get("https://registry.npmjs.org/@types/node").respond(
            status_code=200, json=mock_response
        )
        
        async with NpmConnector() as connector:
            data = await connector.fetch_package("@types/node")
            
        assert data == mock_response
        assert mock_route.called


@pytest.mark.asyncio
async def test_fetch_package_not_found():
    """Test fetching a non-existent package raises PackageNotFoundError."""
    with respx.mock(assert_all_called=True) as mock_respx:
        mock_respx.get("https://registry.npmjs.org/nonexistent-pkg-xyz").respond(
            status_code=404, json={"error": "Not found"}
        )
        
        async with NpmConnector() as connector:
            with pytest.raises(PackageNotFoundError, match="not found"):
                await connector.fetch_package("nonexistent-pkg-xyz")


@pytest.mark.asyncio
async def test_fetch_package_server_error():
    """Test registry returning 500 raises RegistryConnectionError."""
    with respx.mock(assert_all_called=True) as mock_respx:
        mock_respx.get("https://registry.npmjs.org/react").respond(
            status_code=500, text="Internal Server Error"
        )
        
        async with NpmConnector() as connector:
            with pytest.raises(RegistryConnectionError, match="status 500"):
                await connector.fetch_package("react")


@pytest.mark.asyncio
async def test_fetch_package_network_error():
    """Test network failures raise RegistryConnectionError."""
    with respx.mock(assert_all_called=True) as mock_respx:
        mock_respx.get("https://registry.npmjs.org/react").mock(
            side_effect=httpx.ConnectError("Network is down")
        )
        
        async with NpmConnector() as connector:
            with pytest.raises(RegistryConnectionError, match="Failed to request"):
                await connector.fetch_package("react")
