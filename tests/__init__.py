"""Tests for the broadlink component."""
import binascii

from unittest.mock import MagicMock

TEST_DATA_JSON = {
    "test_async_setup_entry": [
        "all_remote_types.json",
        "all_remotes_with_storage_data.json", 
        "locked_remote.json",
        "unavailable_remote.json"
        ],
    "test_main": [
        "add_new_preset_to_new_remote.json", 
        "add_new_preset_to_existing_remote.json",
    ], 
    "test_remove_preset": [
        "remove_preset_from_existing_remote.json"
    ]
}


def convert_mac_into_bytes(mac):
  """Convert Mac from string into bytes"""
  return binascii.unhexlify(mac.replace(':', ''))


def get_mock_api(new_device_fixture):
    """Return a mock device (API)."""
    mock_api = MagicMock()
    mock_api.name = new_device_fixture["name"]
    mock_api.host = (new_device_fixture["host"], 80)
    mock_api.mac = convert_mac_into_bytes(new_device_fixture["mac"])
    mock_api.model = new_device_fixture["model"]
    mock_api.manufacturer = new_device_fixture["manufacturer"]
    mock_api.type = new_device_fixture["type"]
    mock_api.devtype = new_device_fixture["devtype"]
    mock_api.timeout = 10
    mock_api.is_locked = new_device_fixture["device_is_locked"]
    mock_api.auth.return_value = True
    return mock_api