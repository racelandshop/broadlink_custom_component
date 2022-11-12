"""Helpers for the Broadlink remote."""

import broadlink as blk
from broadlink.exceptions import BroadlinkException

from base64 import b64decode

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store

from slugify import slugify

from .const import (ACTIVE, DEVICE_MAC, DEVICE_TYPE, DOMAIN,  LOCKED, MAC, PRESETS, TIMEOUT)


import logging

_LOGGER = logging.getLogger(__name__)

async def discover_devices(hass): 
    """Discover devices connected to the network"""
    devices = blk.discover(timeout = TIMEOUT)
    device_list = []
    for device in devices: 
        formated_mac = format_mac(device.mac)
        try:
            device.auth()
            device.set_lock(False)
        except:
            _LOGGER.error("Erro when trying to authenticate the device %s", formated_mac)
        
        device_list.append(device)

    return device_list
    
def get_active_devices(hass): 
    """Get all active devices and return their information"""
    devices = [] 
    for device_mac,device_data in hass.data[DOMAIN].storage_data.items(): 
        if device_data[ACTIVE]: 
            devices.append({
                MAC: device_mac, 
                DEVICE_TYPE: device_data[DEVICE_TYPE],
                LOCKED: device_data[LOCKED],
                PRESETS: device_data[PRESETS]
            })
    return devices

def decode_packet(value):
    """Decode a data packet given for a Broadlink remote."""
    value = cv.string(value)
    extra = len(value) % 4
    if extra > 0:
        value = value + ("=" * (4 - extra))
    return b64decode(value)

def format_mac(mac):
    """Format a MAC address."""
    return ":".join([format(octet, "02x") for octet in mac])

async def load_from_storage(hass): 
    """Load devices from the storage."""
    store = Store(hass, version = 1, key = "broadlink_devices")
    devices = await store.async_load()
    return devices if devices is not None else {}

async def save_to_storage(hass, data):
    """Save data to storage."""
    store = Store(hass, version = 1, key = "broadlink_devices")
    await store.async_save(data)


def setup_platform(hass, async_add_entities, cls):
   
    def adder(hass, broadlink_data, device, preset_name):
        identifier = slugify(f"{broadlink_data[DEVICE_MAC]}-{preset_name}")
        entity = cls(hass, preset_name, device, broadlink_data, identifier)
        async_add_entities([entity])
        return entity

    hass.data[DOMAIN].adder = adder
    return True


async def create_entity(hass, broadlink_data, device, preset_name):
    adder = hass.data[DOMAIN].adder
    entity = adder(hass, broadlink_data, device, preset_name)
    return entity

