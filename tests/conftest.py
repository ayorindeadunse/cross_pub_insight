import sys
import os
import pytest

# Ensure the project root is always on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Optional: setup a test client fixture
from httpx import AsyncClient
from api.server import app

@pytest.fixture
async def test_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac