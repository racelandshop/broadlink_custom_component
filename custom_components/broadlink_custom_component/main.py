"""Main object of the broadlink itegration that gets passed around"""
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform, CONF_ENTITY_ID
from homeassistant.helpers import entity_registry as er

import logging

from .helpers import format_mac, create_entity
from .const import (ACTIVE, COMMANDS, DEVICE_MAC,
                    DEVICE_TYPE, DOMAINS_AND_TYPES,
                    LOCKED, PRESETS, REMOTE_DOMAIN,
                    TYPE)


_LOGGER = logging.getLogger(__name__)


class RacelandBroadlink: 
    def __init__(self, hass: HomeAssistant, storage_data = {})  -> None:
        self.hass = hass
        self.storage_data = storage_data
        self.adder = None
        self._devices = {}


    async def update_raceland_broadlink_data(self, discover_info: list): 
        """Update the storage data and device list with data in the Device object of the Broadlink API"""
        new_device_flag = False
        for device in discover_info: 
            formated_mac = format_mac(device.mac)
            self._devices[formated_mac] = device
            if formated_mac not in self.storage_data and device.type in DOMAINS_AND_TYPES[Platform.REMOTE]:
                new_device_flag = True
                info = {
                    DEVICE_MAC: formated_mac, 
                    DEVICE_TYPE: device.type,
                    PRESETS: {}, 
                    ACTIVE: True,
                    LOCKED: device.is_locked
                }
                self.storage_data[formated_mac] = info
            
            elif formated_mac in self.storage_data:
                self.storage_data[formated_mac][LOCKED] = device.is_locked 

            elif device.type not in DOMAINS_AND_TYPES[Platform.REMOTE]: 
                _LOGGER.warning("Device of type %s not supported", device.type)

        if new_device_flag: 
            self.hass.components.persistent_notification.async_create(
               "Novos dispositivos Descobertos",
                title= "Descoberta de dispositivos",
                notification_id="device_discover")


        #Deactivate remotes that are are not captured by the network
        mac_list = [format_mac(device.mac) for device in discover_info]
        for registered_mac in self.storage_data.keys(): 
            if registered_mac not in mac_list:
                self.storage_data[registered_mac][ACTIVE] = False
        

    async def add_preset(self, mac,preset_name, remote_type): 
        """Add a new preset to an existing remote and registers entity"""    
        info = {
            COMMANDS: {},
            TYPE: remote_type
            }
        if mac in self.storage_data.keys(): 
            entity_id = get_entity_id(self.hass, preset_name)
            await create_entity(self.hass, self.storage_data[mac], self._devices[mac], preset_name)
            info = {
                COMMANDS: {},
                TYPE: remote_type,
                CONF_ENTITY_ID: entity_id
            }
            self.storage_data[mac][PRESETS][preset_name] = info
            return True
        else: 
            _LOGGER.error("The device with the mac %s is not registered and was not able to add preset", mac)
            return False
    
    async def remove_preset(self, mac, preset_name): 
        if mac in self.storage_data.keys(): 
            entity_id = self.storage_data[mac][PRESETS][preset_name][CONF_ENTITY_ID]
            entity_registry = er.async_get(self.hass)
            
            if not (entity_registry.async_get(entity_id)):
                _LOGGER.error("Entity with entity id %s is not registered", entity_id)
                return False
            else: 
                entity_registry.async_remove(entity_id) #Remove the entity from the registry. 
                del self.storage_data[mac][PRESETS][preset_name]
                return True

        else: 
            _LOGGER.error("The device with the mac %s is not registered and was not able to add preset", mac)
            return False

    async def update_preset(self, mac, preset_name, remote_type = None, new_command = None): 
        """Update the preset."""    
        if mac in self.storage_data.keys(): 
            preset_info = self.storage_data[mac][PRESETS][preset_name]
        else: 
            _LOGGER.error("The device with the mac %s is not registered and was not able to add preset", mac)
            raise OSError
            
        if remote_type != None: 
            preset_info[TYPE] = remote_type
    
        
        if new_command != None: 
            preset_info[COMMANDS].update(new_command)            
        

    @property
    def devices(self): 
        """Return function used to add remote entities"""
        return self._devices

def get_entity_id(hass, entity_name): 
    """Generate entity id that does not conflict"""
    entity_registry = er.async_get(hass)
    return entity_registry.async_generate_entity_id(REMOTE_DOMAIN, entity_name)
