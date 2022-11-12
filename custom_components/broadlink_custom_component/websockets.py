"""Websockets for broadlink custom card"""

import broadlink as blk
from broadlink.exceptions import BroadlinkException

import voluptuous as vol
import logging


from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import async_get_platforms

from .const import (DOMAIN, FAIL_NETWORK_CONNECTION)
                    
from .helpers import discover_devices, get_active_devices, save_to_storage


_LOGGER = logging.getLogger(__name__)

async def setup_websocket(hass):
    hass.components.websocket_api.async_register_command(discover_new_broadlink_devices)
    hass.components.websocket_api.async_register_command(send_broadlink_devices)
    hass.components.websocket_api.async_register_command(enter_broadlink_remote_learning_mode)
    hass.components.websocket_api.async_register_command(add_remote_broadlink)
    hass.components.websocket_api.async_register_command(remove_remote_broadlink)
    return True


@websocket_api.websocket_command({vol.Required("type"): "broadlink/discover"})
@websocket_api.async_response
async def discover_new_broadlink_devices(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Discover broadlink devices"""
    try: 
        device_list = await discover_devices(hass)
        await hass.data[DOMAIN].update_raceland_broadlink_data(device_list) 
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



@websocket_api.websocket_command({
    vol.Required("type"): "broadlink/enter_learning_mode", 
    vol.Required("mac"): str, 
    vol.Required("preset_name"): str,
    vol.Required("entity_id"): str,
    vol.Required("button_name"): str, 
    }
)
@websocket_api.async_response
async def enter_broadlink_remote_learning_mode(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Enter learning mode for a broadlink remote"""  
    mac = msg["mac"]
    preset_name = msg["preset_name"]
    entity_id = msg["entity_id"]
    button_name = msg["button_name"]

    
    entity_platform_integration = async_get_platforms(hass, DOMAIN)
    entity_platform_remote = entity_platform_integration[0].entities #For now I'm only saving remote entities so I can fetch the first element in the list
    remote = entity_platform_remote[entity_id]

    if remote.learning:
        hass.components.persistent_notification.async_create("Já está a configurar um botão. Termine este processo antes de tentar configurar outro.", 
            title="Aviso", 
            notification_id= "learning_mode_warning")
        connection.send_result(msg["id"], {"sucess": False, "code": None})
    else: 
        try: 
            decoded_code = await remote.async_learn_command(button_name)

            raceland_broadlink = hass.data[DOMAIN]
            new_command = {button_name: decoded_code}
            await raceland_broadlink.update_preset(mac, preset_name, new_command = new_command)
            await save_to_storage(hass, raceland_broadlink.storage_data)

            hass.components.persistent_notification.async_dismiss(
                        notification_id="learning_mode_warning"
                    )

            connection.send_result(msg["id"], {"sucess": True, "code": decoded_code})

        except (BroadlinkException, OSError) as err:
            connection.send_result(msg["id"], {"sucess": True, "code": None})    
    

    return


@websocket_api.websocket_command({vol.Required("type"): "broadlink/add_remote", vol.Required("mac"): str, vol.Required("preset"): str, vol.Required("remote_type"): str})
@websocket_api.async_response
async def add_remote_broadlink(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Add a new remote to the preset list"""
    mac = msg["mac"]
    preset_name = msg["preset"]
    remote_type = msg["remote_type"]
    
    raceland_broadlink = hass.data[DOMAIN]
    status = await raceland_broadlink.add_preset(mac,preset_name, remote_type)
    if status: 
        await save_to_storage(hass, raceland_broadlink.storage_data)
        devices = get_active_devices(hass) 
        connection.send_result(msg["id"], {"sucess": True, "devices": devices}) 
    else: 
        connection.send_result(msg["id"], {"sucess": False}) 
    
    

@websocket_api.websocket_command({vol.Required("type"): "broadlink/remove_remote", vol.Required("mac"): str, vol.Required("preset"): str})
@websocket_api.async_response
async def remove_remote_broadlink(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
):
    """Add a new remote to the preset list"""
    mac = msg["mac"]
    preset_name = msg["preset"]
    
    raceland_broadlink = hass.data[DOMAIN]
    status = await raceland_broadlink.remove_preset(mac,preset_name)
    if status: 
        await save_to_storage(hass, raceland_broadlink.storage_data)
        devices = get_active_devices(hass)
        connection.send_result(msg["id"], {"sucess": True, "devices": devices}) 
    else: 
        connection.send_result(msg["id"], {"sucess": False}) 
        