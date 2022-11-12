"""Tests init in broadlink custom component"""
import json

from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.broadlink_custom_component.const import DOMAIN
from custom_components.broadlink_custom_component.main import RacelandBroadlink
from custom_components.broadlink_custom_component import setup_data

from . import TEST_DATA_JSON, get_mock_api


async def test_async_setup_entry(hass): 
    """Test async_setup_entry"""

    # Create a mock entry so we don't have to go through config flow
    config_entry = MockConfigEntry(domain=DOMAIN, data = "", entry_id="setup_test")

  
    for file in TEST_DATA_JSON["test_async_setup_entry"]: 
        #Load device data
        fixture_test = json.loads(load_fixture(file))
    
        storage_data = fixture_test["storage_data"]
        device_data = fixture_test["found_devices"]
        hass_data = fixture_test["hass_data"]        

        #For each device make a Mock objet for testing
        mock_api =  [get_mock_api(dev) for dev in device_data.values()]
    
        #Run tests
        assert await setup_data(hass, entry=config_entry, storage_data=storage_data, device_list=mock_api)
        assert DOMAIN in hass.data and type(hass.data[DOMAIN]) == RacelandBroadlink 
        assert hass.data[DOMAIN].storage_data == hass_data
