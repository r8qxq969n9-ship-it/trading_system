"""Test spec loader."""

import pytest

from packages.brokers.kis_direct.spec_loader import APISpecNotFoundError, SpecLoader


def test_list_available_apis(api_docs_dir):
    """Test listing available APIs."""
    loader = SpecLoader()
    apis = loader.list_available_apis()
    assert isinstance(apis, list)
    assert len(apis) > 0


def test_get_api(api_docs_dir):
    """Test getting API spec."""
    loader = SpecLoader()
    # Try to get an API (if any exists)
    apis = loader.list_available_apis()
    if apis:
        spec = loader.get_api(apis[0])
        assert "api_name" in spec or "tr_id_real" in spec


def test_get_api_not_found(api_docs_dir):
    """Test getting non-existent API."""
    loader = SpecLoader()
    with pytest.raises(APISpecNotFoundError):
        loader.get_api("NON_EXISTENT_API")
