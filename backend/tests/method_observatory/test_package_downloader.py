import pytest
import respx
import httpx
from pathlib import Path
import tempfile
import tarfile
import zipfile
import os

from app.method_observatory.ingestion.package_downloader import PackageDownloader

@pytest.fixture
def downloader():
    return PackageDownloader()

@pytest.mark.asyncio
@respx.mock
async def test_get_package_info_success(downloader):
    url = "https://pypi.org/pypi/testpkg/1.0.0/json"
    respx.get(url).mock(return_value=httpx.Response(200, json={"urls": []}))
    
    info = await downloader._get_package_info("testpkg", "1.0.0")
    assert "urls" in info

@pytest.mark.asyncio
@respx.mock
async def test_get_package_info_404(downloader):
    url = "https://pypi.org/pypi/testpkg/1.0.0/json"
    respx.get(url).mock(return_value=httpx.Response(404))
    
    with pytest.raises(ValueError, match="not found on PyPI"):
        await downloader._get_package_info("testpkg", "1.0.0")

def test_find_source_distribution(downloader):
    releases = [
        {"packagetype": "bdist_wheel", "url": "wheel.whl"},
        {"packagetype": "sdist", "url": "src.tar.gz"}
    ]
    sdist = downloader._find_source_distribution(releases)
    assert sdist["url"] == "src.tar.gz"
    
    assert downloader._find_source_distribution([{"packagetype": "bdist"}]) is None

@pytest.mark.asyncio
@respx.mock
async def test_download_and_extract_tar_gz(downloader):
    # Setup mock registry response
    info_url = "https://pypi.org/pypi/testpkg/1.0.0/json"
    respx.get(info_url).mock(return_value=httpx.Response(200, json={
        "urls": [{"packagetype": "sdist", "url": "https://pypi.org/testpkg-1.0.0.tar.gz", "filename": "testpkg-1.0.0.tar.gz"}]
    }))
    
    # Setup mock file download response
    download_url = "https://pypi.org/testpkg-1.0.0.tar.gz"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create a real dummy tar.gz file
        dummy_tar_path = tmp_path / "dummy.tar.gz"
        with tarfile.open(dummy_tar_path, "w:gz") as tar:
            # Create a file inside a dummy dir
            os.makedirs(tmp_path / "testpkg-1.0.0", exist_ok=True)
            dummy_inner = tmp_path / "testpkg-1.0.0" / "test.py"
            dummy_inner.write_text("print('hello')")
            tar.add(tmp_path / "testpkg-1.0.0", arcname="testpkg-1.0.0")
            
        with open(dummy_tar_path, "rb") as f:
            tar_bytes = f.read()
            
        respx.get(download_url).mock(return_value=httpx.Response(200, content=tar_bytes))
        
        extracted_dir = await downloader.download_and_extract("testpkg", "1.0.0", tmp_path)
        
        assert extracted_dir.exists()
        assert extracted_dir.name == "testpkg-1.0.0"
        assert (extracted_dir / "test.py").exists()

@pytest.mark.asyncio
@respx.mock
async def test_download_and_extract_zip(downloader):
    # Setup mock registry response
    info_url = "https://pypi.org/pypi/testpkg/1.0.0/json"
    respx.get(info_url).mock(return_value=httpx.Response(200, json={
        "urls": [{"packagetype": "sdist", "url": "https://pypi.org/testpkg-1.0.0.zip", "filename": "testpkg-1.0.0.zip"}]
    }))
    
    download_url = "https://pypi.org/testpkg-1.0.0.zip"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        dummy_zip_path = tmp_path / "dummy.zip"
        with zipfile.ZipFile(dummy_zip_path, "w") as zf:
            zf.writestr("testpkg-1.0.0/test.py", "print('hello')")
            
        with open(dummy_zip_path, "rb") as f:
            zip_bytes = f.read()
            
        respx.get(download_url).mock(return_value=httpx.Response(200, content=zip_bytes))
        
        extracted_dir = await downloader.download_and_extract("testpkg", "1.0.0", tmp_path)
        
        assert extracted_dir.exists()
        assert extracted_dir.name == "testpkg-1.0.0"

@pytest.mark.asyncio
@respx.mock
async def test_download_and_extract_no_sdist(downloader):
    info_url = "https://pypi.org/pypi/testpkg/1.0.0/json"
    respx.get(info_url).mock(return_value=httpx.Response(200, json={
        "urls": [{"packagetype": "bdist", "url": "...", "filename": "testpkg.whl"}]
    }))
    
    with pytest.raises(ValueError, match="No source distribution found"):
        await downloader.download_and_extract("testpkg", "1.0.0", Path("/tmp"))

@pytest.mark.asyncio
@respx.mock
async def test_download_and_extract_unknown_format(downloader):
    info_url = "https://pypi.org/pypi/testpkg/1.0.0/json"
    respx.get(info_url).mock(return_value=httpx.Response(200, json={
        "urls": [{"packagetype": "sdist", "url": "https://pypi.org/testpkg-1.0.0.rar", "filename": "testpkg-1.0.0.rar"}]
    }))
    download_url = "https://pypi.org/testpkg-1.0.0.rar"
    respx.get(download_url).mock(return_value=httpx.Response(200, content=b"fake"))
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="Unknown archive format"):
            await downloader.download_and_extract("testpkg", "1.0.0", Path(tmpdir))
