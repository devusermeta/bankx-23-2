"""Pytest configuration and fixtures for A2A tests."""
import pytest


@pytest.fixture
def mock_registry_url():
    """Mock agent registry URL."""
    return "http://localhost:9000"


@pytest.fixture
def mock_customer_id():
    """Mock customer ID for tests."""
    return "CUST-TEST-001"
