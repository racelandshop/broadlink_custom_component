"""Tests init in broadlink custom component"""
import json
import pytest 
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.broadlink_custom_component.const import DOMAIN
from custom_components.broadlink_custom_component import setup_data


from . import TEST_DATA_JSON, get_mock_api

@pytest.mark.asyncio
async def test_add_preset(hass): 
    """Test async_add_preset"""

    # Create a mock entry so we don't have to go through config flow
    config_entry = MockConfigEntry(domain=DOMAIN, data = "", entry_id="setup_test")

  
    for file in TEST_DATA_JSON["test_main"]: 
        #Load device data
        fixture_test = json.loads(load_fixture(file))
    
        device_data = fixture_test["found_devices"]
        storage_data = fixture_test.get("storage_data", {})
        new_preset_data = fixture_test["preset"]
        hass_data = fixture_test["hass_data"]        
        
        #For each device make a Mock objet for testing
        mock_api =  [get_mock_api(dev) for dev in device_data.values()]

        #Setup main object
        await setup_data(hass, entry=config_entry, storage_data=storage_data, device_list=mock_api)

        with patch("custom_components.broadlink_custom_component.main.create_entity"): 
            #Add remote 
            assert await hass.data[DOMAIN].add_preset(new_preset_data["mac"], new_preset_data["name"], new_preset_data["type"]) == True
            #Check storage data in main
            assert hass.data[DOMAIN].storage_data == hass_data

@pytest.mark.asyncio
async def test_remove_preset(hass): 
    """Test async_remove_preset"""

    # Create a mock entry so we don't have to go through config flow
    config_entry = MockConfigEntry(domain=DOMAIN, data = "", entry_id="setup_test")

  
    for file in TEST_DATA_JSON["test_remove_preset"]: 
        #Load device data
        fixture_test = json.loads(load_fixture(file))
    
        device_data = fixture_test["found_devices"]
        storage_data = fixture_test.get("storage_data", {})
        remove_preset_data = fixture_test["preset"]
        hass_data = fixture_test["hass_data"]        
        
        #For each device make a Mock objet for testing
        mock_api =  [get_mock_api(dev) for dev in device_data.values()]

        #Setup main object
        await setup_data(hass, entry=config_entry, storage_data=storage_data, device_list=mock_api)

        with patch(
            "homeassistant.helpers.entity_registry.EntityRegistry.async_get", 
            return_value=True
            ),patch(
                "homeassistant.helpers.entity_registry.EntityRegistry.async_remove"
                ): 
            #Remove preset
            assert await hass.data[DOMAIN].remove_preset(remove_preset_data["mac"], remove_preset_data["name"]) == True
            #Check storage data in main
            assert hass.data[DOMAIN].storage_data == hass_data

    