"""The broadlink card integration"""

from .const import DEVICE_STORAGE, TIMEOUT, DOMAIN, DOMAINS_AND_TYPES, DEVICE_INFO, COMMANDS, MAC, DEVICE_MAC, DEVICE_TYPE
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

##Improvement: save the devices and not the device data in hass.data. Perform auth() during setup. 


##TODO: Type-hinting
##TODO: Implement error handling
##TODO: Possibly create a remote entity
##TODO: Limit search to remotes and not other broadlink devices! <- IMPORTANTE
##TODO: Handling the toggle command

async def async_setup(hass, config):
    """Setup broadlink integration"""

    #TODO: The card in the frontend should not be available until the discovery process is done.

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][DEVICE_STORAGE] = await load_from_storage(hass)
    hass.data[DOMAIN][DEVICE_INFO] = {}
    devices = blk.discover(timeout = TIMEOUT)
    for device in devices: 
        try: 
            _LOGGER.info("Current storage information is: %s", hass.data[DOMAIN][DEVICE_STORAGE])
            formated_mac = format_mac(device.mac)
            if formated_mac not in hass.data[DOMAIN][DEVICE_STORAGE] and device.type in DOMAINS_AND_TYPES[Platform.REMOTE]:
                _LOGGER.warning("New device found: %s", formated_mac)
                info = {
                DEVICE_MAC: formated_mac, 
                DEVICE_TYPE: device.type,
                COMMANDS: {} 
                }

                hass.data[DOMAIN][DEVICE_STORAGE][formated_mac] = info
                hass.data[DOMAIN][DEVICE_INFO][formated_mac] = BroadlinkRemote(hass, device, commands)
            
            elif formated_mac in hass.data[DOMAIN][DEVICE_STORAGE]:
                _LOGGER.warning("Device already in storage, fecthing commands")
                commands = hass.data[DOMAIN][DEVICE_STORAGE][formated_mac][COMMANDS]
                hass.data[DOMAIN][DEVICE_INFO][formated_mac] = BroadlinkRemote(hass, device, commands)
            
            elif device.type not in DOMAINS_AND_TYPES[Platform.REMOTE]: 
                _LOGGER.warning("Device of type %s not supported", device.type)

        except: #TODD: Improve error handling
            _LOGGER.info("Device could mac not be reached %s.", device)

    await save_to_storage(hass, hass.data[DOMAIN][DEVICE_STORAGE])

    hass.components.websocket_api.async_register_command(discover_new_broadlink_devices)
    hass.components.websocket_api.async_register_command(send_broadlink_devices)
    hass.components.websocket_api.async_register_command(enter_broadlink_remote_learning_mode)
    hass.components.websocket_api.async_register_command(send_command_broadlink)
    return True


@websocket_api.websocket_command({vol.Required("type"): "broadlink/discover"})
@websocket_api.async_response
async def discover_new_broadlink_devices(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Discover broadlink devices"""

    devices = blk.discover(timeout = TIMEOUT) 
    device_info = {}
    for device in devices:
        if device.type in DOMAINS_AND_TYPES[Platform.REMOTE]:
            formated_mac = format_mac(device.mac)
            device_info[formated_mac] = {
                DEVICE_MAC: formated_mac, 
                DEVICE_TYPE: device.type,
                COMMANDS: {} 
            }
        else: 
            _LOGGER.debug("The device type %s is being ignored", device.type)

        hass.data[DOMAIN][DEVICE_INFO][DEVICE_MAC] = BroadlinkRemote(hass, device)
    
    hass.data[DOMAIN][DEVICE_STORAGE] = device_info
    await save_to_storage(hass, device_info)
    

    connection.send_result(msg["id"], {"sucess": True, "n_devices": len(device_info)}) ##TODO: Send device data to save in the frontend


#TODO: Not sure if this function will be required 
@websocket_api.websocket_command({vol.Required("type"): "broadlink/send_devices"})
@websocket_api.async_response
async def send_broadlink_devices(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Send saved broadlink devices to the frontend"""  
    devices = hass.data[DOMAIN][DEVICE_STORAGE]
    connection.send_result(msg["id"], {"sucess": True, "devices": devices}) 


@websocket_api.websocket_command({vol.Required("type"): "broadlink/enter_learning_mode", vol.Required("mac"): str, vol.Required("button_name"): str})
@websocket_api.async_response
async def enter_broadlink_remote_learning_mode(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Enter learning mode for a broadlink remote"""  
    mac = msg["mac"]
    button_name = msg["button_name"]
    remote = hass.data[DOMAIN][DEVICE_INFO].get(mac)
    decoded_code = await remote.learn_command()

    hass.data[DOMAIN][DEVICE_INFO][mac] = remote
    hass.data[DOMAIN][DEVICE_STORAGE][mac].update({button_name: decoded_code})
    
    sucess = True if decoded_code else False
    _LOGGER.info(decoded_code)
    connection.send_result(msg["id"], {"sucess": sucess}) 


@websocket_api.websocket_command({vol.Required("type"): "broadlink/send_command", vol.Required("mac"): str, vol.Required("button_name"): str})
@websocket_api.async_response
async def send_command_broadlink(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Send a command to a broadlink remote"""
    remote = hass.data[DOMAIN][DEVICE_INFO].get([msg["mac"]]) 
    if remote: 
        remote.send_command(msg["button_name"])
    else: 
        _LOGGER.error("The device with the mac %s is not registered", msg["mac"])
    

async def save_to_storage(hass, data):
    """Save data to storage."""
    store = Store(hass, version = 1, key = "broadlink_devices")
    await store.async_save(data)


async def load_from_storage(hass): 
    """Load devices from the storage."""
    store = Store(hass, version = 1, key = "broadlink_devices")
    devices = await store.async_load()
    return devices if devices is not None else {}

