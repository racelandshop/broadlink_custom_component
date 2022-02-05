"""The broadlink card integration"""

from pickle import TRUE
from .const import DEVICE_JSON, TIMEOUT, DOMAIN, DOMAINS_AND_TYPES, DEVICE_INFO, PRESETS, MAC, DEVICE_MAC, DEVICE_TYPE, ACTIVE
from .remote import BroadlinkRemote
from .helpers import format_mac

import asyncio
from base64 import b64encode, b64decode
import broadlink as blk

from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store

import logging
import voluptuous as vol



_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Setup broadlink integration"""


    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][DEVICE_JSON] = await load_from_storage(hass)
    hass.data[DOMAIN][DEVICE_INFO] = {}
    await discover_devices(hass)

    hass.components.websocket_api.async_register_command(discover_new_broadlink_devices)
    hass.components.websocket_api.async_register_command(send_broadlink_devices)
    hass.components.websocket_api.async_register_command(enter_broadlink_remote_learning_mode)
    hass.components.websocket_api.async_register_command(send_command_broadlink)
    return True



async def discover_devices(hass): 
    """Discover devices in the network and update the list"""
    
    devices = blk.discover(timeout = TIMEOUT)
    for device in devices: 
        try: 
            formated_mac = format_mac(device.mac)
            if formated_mac not in hass.data[DOMAIN][DEVICE_JSON] and device.type in DOMAINS_AND_TYPES[Platform.REMOTE]:
                _LOGGER.warning("New device found: %s", formated_mac)
                info = {
                    DEVICE_MAC: formated_mac, 
                    DEVICE_TYPE: device.type,
                    PRESETS: {"1": {}, "2": {}, "3": {}, "4": {}, "5": {}}, 
                    ACTIVE: True
                }

                hass.data[DOMAIN][DEVICE_JSON][formated_mac] = info
                hass.data[DOMAIN][DEVICE_INFO][formated_mac] = BroadlinkRemote(hass, device, preset_info)
            
            elif formated_mac in hass.data[DOMAIN][DEVICE_JSON]:
                _LOGGER.warning("Device already in storage, fecthing commands presets")
                preset_info = hass.data[DOMAIN][DEVICE_JSON][formated_mac][PRESETS]
                hass.data[DOMAIN][DEVICE_JSON][formated_mac][ACTIVE] = True
                hass.data[DOMAIN][DEVICE_INFO][formated_mac] = BroadlinkRemote(hass, device, preset_info)
            
            elif device.type not in DOMAINS_AND_TYPES[Platform.REMOTE]: 
                _LOGGER.warning("Device of type %s not supported", device.type)

        except: #TODO: Improve error handling
            _LOGGER.info("Device could mac not be reached %s.", device)


    #Deactivate devices that are are not captured by the network
    mac_list = [format_mac(device.mac) for device in devices]
    for registered_mac in hass.data[DOMAIN][DEVICE_JSON].keys(): 
        if registered_mac not in mac_list:
            hass.data[DOMAIN][DEVICE_JSON][registered_mac][ACTIVE] = False


    await save_to_storage(hass, hass.data[DOMAIN][DEVICE_JSON])
    


@websocket_api.websocket_command({vol.Required("type"): "broadlink/discover"})
@websocket_api.async_response
async def discover_new_broadlink_devices(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Discover broadlink devices"""

    await discover_devices(hass)
    devices = get_active_devices(hass) 
    connection.send_result(msg["id"], {"sucess": True, "devices": devices}) 


@websocket_api.websocket_command({vol.Required("type"): "broadlink/send_devices"})
@websocket_api.async_response
async def send_broadlink_devices(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Send saved broadlink devices to the frontend"""  
    devices = get_active_devices(hass)
    connection.send_result(msg["id"], {"sucess": True, "devices": devices}) 


@websocket_api.websocket_command({vol.Required("type"): "broadlink/enter_learning_mode", vol.Required("mac"): str, vol.Required("button_name"): str, vol.Required("preset"): str})
@websocket_api.async_response
async def enter_broadlink_remote_learning_mode(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Enter learning mode for a broadlink remote"""  
    mac = msg["mac"]
    button_name = msg["button_name"]
    preset = msg["preset"]
    remote = hass.data[DOMAIN][DEVICE_INFO][mac]
    decoded_code = await remote.learn_command(button_name, preset)
    hass.data[DOMAIN][DEVICE_JSON][mac][PRESETS][preset].update({button_name: decoded_code})
    await save_to_storage(hass, hass.data[DOMAIN][DEVICE_JSON])
    connection.send_result(msg["id"], {"code": decoded_code}) 


@websocket_api.websocket_command({vol.Required("type"): "broadlink/send_command", vol.Required("mac"): str, vol.Required("button_name"): str, vol.Required("preset"): str})
@websocket_api.async_response
async def send_command_broadlink(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Send a command to a broadlink remote"""
    mac = msg["mac"]
    button_name = msg["button_name"]
    preset = msg["preset"]
    remote = hass.data[DOMAIN][DEVICE_INFO][mac]
    if remote: 
        await remote.send_command(button_name, preset)
    else: 
        _LOGGER.error("The device with the mac %s is not registered", msg["mac"])
        connection.send_result(msg["id"], {"sucess": False}) 
    
    connection.send_result(msg["id"], {"sucess": True}) 
    

def get_active_devices(hass): 
    """Get all active devices and return their information"""
    devices = [] 
    for device_mac in hass.data[DOMAIN][DEVICE_JSON]: 
        if hass.data[DOMAIN][DEVICE_JSON][device_mac][ACTIVE]: 
            devices.append({
                MAC: device_mac, 
                DEVICE_TYPE: hass.data[DOMAIN][DEVICE_JSON][device_mac][DEVICE_TYPE],
                #PRESETS: len(hass.data[DOMAIN][DEVICE_JSON][device_mac][PRESETS])
            })
    return devices
            
async def save_to_storage(hass, data):
    """Save data to storage."""
    store = Store(hass, version = 1, key = "broadlink_devices")
    await store.async_save(data)


async def load_from_storage(hass): 
    """Load devices from the storage."""
    store = Store(hass, version = 1, key = "broadlink_devices")
    devices = await store.async_load()
    return devices if devices is not None else {}

