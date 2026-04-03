import pytest
from puppet_ai.core.cdp import CDPClient

def test_cdp_client_init():
    client = CDPClient(port=9222)
    assert client.port == 9222
    assert client._ws is None
    assert client.connected is False

def test_cdp_client_custom_port():
    client = CDPClient(port=9333)
    assert client.port == 9333
