"""The broadlink custom card integration"""

import logging

from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (DOMAIN,FAIL_NETWORK_CONNECTION)
from .helpers import discover_devices, load_from_storage, save_to_storage
from .main import RacelandBroadlink
from .websockets import setup_websocket

from broadlink.exceptions import (
    BroadlinkException,
)


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Setup broadlink integration"""
    storage_data = await load_from_storage(hass)
    
    try: 
        device_list = await discover_devices(hass)
    except BroadlinkException: 
        _LOGGER.warning(FAIL_NETWORK_CONNECTION)    
    
    await setup_data(hass, entry, storage_data, device_list)

    return True


async def setup_data(hass, entry: ConfigEntry, storage_data, device_list): 
    """Setup RacelandBroadlink object"""
    hass.data[DOMAIN] = raceland_broadlink = RacelandBroadlink(hass, storage_data)

    try: 
        await raceland_broadlink.update_raceland_broadlink_data(device_list) 
        await save_to_storage(hass, raceland_broadlink.storage_data)
    except OSError: 
        _LOGGER.warning("Issue with I/O .storage files.")
        
    await setup_websocket(hass) 

    hass.config_entries.async_setup_platforms(
        entry,
        [Platform.REMOTE]
    )

    return raceland_broadlink.storage_data
