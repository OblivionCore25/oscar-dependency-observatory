import pytest
import respx
import httpx

from app.ingestion.pypi import PypiConnector
from app.normalization.pypi_normalizer import PypiNormalizer

MOCK_PYPI_RESPONSE = {
    "info": {
        "name": "fastapi",
        "version": "0.103.1",
        "requires_dist": [
            "pydantic (!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4)",
            "starlette (>=0.27.0,<0.28.0)",
            "typing-extensions (>=4.5.0)",
            "httpx (>=0.23.0) ; extra == 'all'",
            "pytest (>=7.1.3) ; extra == 'test'"
        ]
    }
}

@pytest.mark.asyncio
@respx.mock
async def test_pypi_connector_fetch_success():
    """Verify PyPI HTTP responses are mapped into standard JSON dicts cleanly."""
    respx.get("https://pypi.org/pypi/fastapi/0.103.1/json").mock(
        return_value=httpx.Response(200, json=MOCK_PYPI_RESPONSE)
    )
    
    async with PypiConnector() as connector:
        data = await connector.fetch_package("fastapi", "0.103.1")
        
    assert data["info"]["name"] == "fastapi"


def test_pypi_normalization_logic():
    """Verify PEP 508 strings map reliably while filtering testing environments."""
    package, versions, edges = PypiNormalizer.normalize_package_data(MOCK_PYPI_RESPONSE)
    
    assert package.name == "fastapi"
    assert package.ecosystem == "pypi"
    
    version = versions[0]
    assert version.version == "0.103.1"
    
    # We expect 4 edges returned (test extra should be filtered softly)
    assert len(edges) == 4
    
    targets = [e.target_package for e in edges]
    assert "pydantic" in targets
    assert "starlette" in targets
    assert "typing-extensions" in targets
    assert "httpx" in targets
    assert "pytest" not in targets
    
    # Check constraint logic
    star_edge = next(e for e in edges if e.target_package == "starlette")
    assert star_edge.version_constraint == ">=0.27.0,<0.28.0"
