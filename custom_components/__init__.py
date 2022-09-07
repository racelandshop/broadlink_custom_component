"""The broadlink card integration"""

from pickle import FALSE, TRUE
from token import COMMA
from .const import DEVICE_JSON, LOCKED, TIMEOUT, DOMAIN, DOMAINS_AND_TYPES, DEVICE_INFO, PRESETS, MAC, DEVICE_MAC, DEVICE_TYPE, ACTIVE, FAIL_NETWORK_CONNECTION, COMMANDS, TYPE
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

from broadlink.exceptions import (
    BroadlinkException,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Setup broadlink integration"""

    _LOGGER.info("hey, I am running", hass.data)
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][DEVICE_JSON] = await load_from_storage(hass)
    hass.data[DOMAIN][DEVICE_INFO] = {}
    #print("hey", hass.data[DOMAIN][DEVICE_JSON])
    try: 
        await discover_devices(hass)
    except OSError: 
        _LOGGER.warning(FAIL_NETWORK_CONNECTION)
        await save_to_storage(hass, hass.data[DOMAIN][DEVICE_JSON])
        
    
    finally: 
        hass.components.websocket_api.async_register_command(discover_new_broadlink_devices)
        hass.components.websocket_api.async_register_command(send_broadlink_devices)
        hass.components.websocket_api.async_register_command(enter_broadlink_remote_learning_mode)
        hass.components.websocket_api.async_register_command(send_command_broadlink)
        hass.components.websocket_api.async_register_command(add_remote_broadlink)
        hass.components.websocket_api.async_register_command(remove_remote_broadlink)
        #_LOGGER.info("hey, I ran") 
        return True



async def discover_devices(hass): 
    """Discover devices in the network and update the list"""
    
    devices = blk.discover(timeout = TIMEOUT)
    new_devices = False
    #_LOGGER.info("STARTED TO DISCOVER", devices) 
    print('DEVICES', devices)
    for device in devices: 

        formated_mac = format_mac(device.mac)
        try:
            device.auth()
            device.set_lock(False)
        except:
            print()
        #_LOGGER.info("ACTIVE", hass.data[DOMAIN][DEVICE_JSON])
        if formated_mac not in hass.data[DOMAIN][DEVICE_JSON] and device.type in DOMAINS_AND_TYPES[Platform.REMOTE]:
            _LOGGER.debug("New device found: %s", formated_mac)
            new_devices = True
            info = {
                DEVICE_MAC: formated_mac, 
                DEVICE_TYPE: device.type,
                PRESETS: {}, 
                ACTIVE: True,
                LOCKED: device.is_locked
            }
            hass.data[DOMAIN][DEVICE_JSON][formated_mac] = info
            hass.data[DOMAIN][DEVICE_JSON][formated_mac][LOCKED] = device.is_locked
            hass.data[DOMAIN][DEVICE_INFO][formated_mac] = BroadlinkRemote(hass, device, info[PRESETS])
            print('DEVICES new',info[PRESETS] )
        
        elif formated_mac in hass.data[DOMAIN][DEVICE_JSON]:
            preset_info = hass.data[DOMAIN][DEVICE_JSON][formated_mac][PRESETS]
            hass.data[DOMAIN][DEVICE_JSON][formated_mac][ACTIVE] = True
            hass.data[DOMAIN][DEVICE_JSON][formated_mac][LOCKED] = device.is_locked
            hass.data[DOMAIN][DEVICE_INFO][formated_mac] = BroadlinkRemote(hass, device, preset_info)
            print('PRESETS', preset_info)
            # print('DEVICES old', hass.data[DOMAIN][DEVICE_JSON][formated_mac][DEVICE_TYPE])
        
        elif device.type not in DOMAINS_AND_TYPES[Platform.REMOTE]: 
            _LOGGER.warning("Device of type %s not supported", device.type)

        
        if new_devices: 
            hass.components.persistent_notification.async_create(
                "Novos despositivos descobertos",
                title="Descoberta de dispositivos",
                notification_id="device_discover",
            )

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
    try: 
        _LOGGER.info("DISCOVERY") 
        await discover_devices(hass)
        devices = get_active_devices(hass)
        connection.send_result(msg["id"], {"sucess": True, "devices": devices}) 
    except OSError: 
        _LOGGER.warning(FAIL_NETWORK_CONNECTION)
        connection.send_result(msg["id"], {"sucess": False, "devices": []}) 


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
    if remote.learning:
        hass.components.persistent_notification.async_create("Já está a configurar um botão. Termine este processo antes de tentar configurar outro.", 
            title="Aviso", 
            notification_id= "learning_mode_warning")
        connection.send_result(msg["id"], {"sucess": False, "code": None})
    else: 
        try: 
            decoded_code = await remote.learn_command(button_name, preset)
            hass.data[DOMAIN][DEVICE_JSON][mac][PRESETS][preset][COMMANDS].update({button_name: decoded_code})
            await save_to_storage(hass, hass.data[DOMAIN][DEVICE_JSON])
            hass.components.persistent_notification.async_dismiss(
                        notification_id="learning_mode_warning"
                    )
            connection.send_result(msg["id"], {"sucess": True, "code": decoded_code})
        except (BroadlinkException, OSError) as err:
            connection.send_result(msg["id"], {"sucess": True, "code": None})


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
    command = remote.preset_list[preset][COMMANDS]
    if remote: 
        await remote.send_command(button_name, preset)
    else: 
        _LOGGER.error("The device with the mac %s is not registered", msg["mac"])
        connection.send_result(msg["id"], {"sucess": False}) 
        return 
    
    connection.send_result(msg["id"], {"sucess": True})

@websocket_api.websocket_command({vol.Required("type"): "broadlink/add_remote", vol.Required("mac"): str, vol.Required("preset"): str, vol.Required("remote_type"): str})
@websocket_api.async_response
async def add_remote_broadlink(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Add a new remote to the preset list"""
    mac = msg["mac"]
    preset = msg["preset"]
    remote_type = msg["remote_type"]
    remote = hass.data[DOMAIN][DEVICE_INFO][mac]
    if remote: 
        print("before remote.preset_list", remote.preset_list)
        remote.preset_list[preset]= {}
        remote.preset_list[preset][COMMANDS]= {}
        remote.preset_list[preset][TYPE]= remote_type
        print("after remote.preset_list", remote.preset_list)
    else: 
        _LOGGER.error("The device with the mac %s is not registered and was not able to add preset", msg["mac"])
        connection.send_result(msg["id"], {"sucess": False}) 
        return
    
    devices = get_active_devices(hass)
    connection.send_result(msg["id"], {"sucess": True, "devices": devices}) 
    await save_to_storage(hass, hass.data[DOMAIN][DEVICE_JSON])

@websocket_api.websocket_command({vol.Required("type"): "broadlink/remove_remote", vol.Required("mac"): str, vol.Required("preset"): str})
@websocket_api.async_response
async def remove_remote_broadlink(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Add a new remote to the preset list"""
    mac = msg["mac"]
    preset = msg["preset"]
    remote = hass.data[DOMAIN][DEVICE_INFO][mac]
    if remote: 
        print("before remote.preset_list", remote.preset_list)
        print("preset", preset)
        del remote.preset_list[preset]
        print("after remote.preset_list", remote.preset_list)
    else: 
        _LOGGER.error("The device with the mac %s is not registered and was not able to remove preset", msg["mac"])
        connection.send_result(msg["id"], {"sucess": False}) 
        return
    
    devices = get_active_devices(hass)
    connection.send_result(msg["id"], {"sucess": True, "devices": devices}) 
    await save_to_storage(hass, hass.data[DOMAIN][DEVICE_JSON])
    

def get_active_devices(hass): 
    """Get all active devices and return their information"""
    devices = [] 
    for device_mac in hass.data[DOMAIN][DEVICE_JSON]: 
        if hass.data[DOMAIN][DEVICE_JSON][device_mac][ACTIVE]: 
            devices.append({
                MAC: device_mac, 
                DEVICE_TYPE: hass.data[DOMAIN][DEVICE_JSON][device_mac][DEVICE_TYPE],
                LOCKED: hass.data[DOMAIN][DEVICE_JSON][device_mac][LOCKED],
                PRESETS: hass.data[DOMAIN][DEVICE_INFO][device_mac].preset_list
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
