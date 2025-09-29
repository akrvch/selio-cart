import os
import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.skip("Basic placeholder; integration tests require running server and DB")
async def test_placeholder():
    assert True


