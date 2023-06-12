"""Support for Broadlink remotes."""

import asyncio

from time import time
from timeit import default_timer

from .const import COMMANDS, DOMAIN, DEVICE_MAC, MAC, PRESETS
from .helpers import decode_packet, setup_platform, create_entity
from .services import setup_services

from base64 import b64encode, b64decode
from broadlink.exceptions import (
    AuthorizationError,
    BroadlinkException,
    ConnectionClosedError,
    ReadError,
    StorageError
)
from broadlink.remote import rmpro

from datetime import timedelta
from functools import partial

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.util import dt

from homeassistant.components.remote import (
    SUPPORT_DELETE_COMMAND,
    SUPPORT_LEARN_COMMAND,
    RemoteEntity
)
import logging


_LOGGER = logging.getLogger(__name__)

LEARNING_TIMEOUT_RMPRO = timedelta(seconds=30)
LEARNING_TIMEOUT = timedelta(seconds=40)

async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the remote platform."""
    return setup_platform(hass, async_add_devices, BroadlinkRemote)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the remote platform from a config entry."""
    #Load up remote entities from storage. 
    await async_setup_platform(hass, {}, async_add_entities)

    await setup_services()

    broadlinks = hass.data[DOMAIN].storage_data
    devices_api = hass.data[DOMAIN].devices

    for broadlink_data in broadlinks.values(): 
        broadlink_preset = broadlink_data[PRESETS]
        device = devices_api[broadlink_data[DEVICE_MAC]]
        for preset_name in broadlink_preset.keys():
            await create_entity(hass, broadlink_data, device, preset_name)



class BroadlinkRemote(RemoteEntity):
    """Representation of a Broadlink remote"""

    def __init__(self, hass, preset_name, device, broadlink_data, identifier):
        """Initialize the entity."""
        self.hass  = hass
        self.device = device
        self.broadlink_data = broadlink_data
        self.learning_lock = False 
        self.learning = False
        self.learningTimeout = LEARNING_TIMEOUT_RMPRO if isinstance(self.device, rmpro) else LEARNING_TIMEOUT
        
        self._attr_name = preset_name
        self._attr_is_on = False
        self._attr_supported_features = SUPPORT_LEARN_COMMAND | SUPPORT_DELETE_COMMAND
        self._attr_unique_id = identifier

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self.broadlink_data[DEVICE_MAC])},
            manufacturer="broadlink",
            name=device.model,
        )

    async def async_turn_on(self, **kwargs):
        """Turn on the remote."""
        self._attr_is_on = True
        self.async_write_ha_state()
        await self.async_send_command("Power")
        
        await asyncio.sleep(1)
        await self.async_turn_off()

    async def async_turn_off(self, **kwargs):
        """Turn of the remote."""
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_send_command(self, button_name): 
        """Send a command with the button name"""
        command_list = self.broadlink_data[PRESETS][self._attr_name][COMMANDS] 
        code = command_list.get(button_name, None)
        if code is None:
            self.hass.components.persistent_notification.async_create(
                "Nennhum comando registado para o butão '{}'".format(button_name),
                title="Envio de comando",
                notification_id="send_command_missing",
                ) 
            return 
        try:
            code = decode_packet(code)
            await self.async_request(self.device.send_data, code)
        except (BroadlinkException, OSError) as err:
            _LOGGER.debug("Error during send_command: %s", err)

    async def async_learn_command(self, button_name): 
        """"Learn a command from the device. Updates the self.learning state of the instance. 
        self.learning_locks acts as a lock to prevent the learning process to co-occur"""
        self.learning_lock = True
        try: 
            return await self._learn_command(button_name)
        except (BroadlinkException, OSError) as err:
            raise
        finally: 
            self.learning_lock = False


    async def _learn_command(self, button_name): 
        """Learn command from the device.
        Returns code"""
        try: 
            await self.async_request(self.device.enter_learning)
        except (BroadlinkException, OSError) as err:
            self.learning_lock = False
            self.hass.components.persistent_notification.async_create(f"Erro ao entrar em modo de aprendizagem. Verifique que comando universal da broadlink ({self.device.type}) está conectada", 
                title="Erro", notification_id="learn_command_error")
            raise

        self.hass.components.persistent_notification.async_create(
           f"Pressione um botão do seu dispositivo para ser aprendido por {self.device.type}",
           title="Aprender comando",
           notification_id="learn_command",
        )
        code = None
        start_time = dt.utcnow()
        while (dt.utcnow() - start_time) < LEARNING_TIMEOUT:
            await asyncio.sleep(1)
            try:
                code = await self.async_request(self.device.check_data)
            except (ReadError, StorageError):
                continue
            
            decoded_code = b64encode(code).decode("utf8")

            self.hass.components.persistent_notification.async_dismiss(
               notification_id="learn_command"
            )
            return decoded_code

        if isinstance(self.device, rmpro): 
            await self.async_request(self.device.cancel_sweep_frequency)

        self.hass.components.persistent_notification.async_create(
            f"O dispositivo {self.device.type} não capturou nenhum comando. Tente novamente",
            title="Aprender comando",
            notification_id="learn_command",
        )


    async def async_request(self, function, *args, **kwargs):
        """Send a request to the device."""
        request = partial(function, *args, **kwargs)
        try:
            return await self.hass.async_add_executor_job(request)
        except (AuthorizationError, ConnectionClosedError):
            if not await self.async_auth():
                raise
            return await self.hass.async_add_executor_job(request)


    async def async_auth(self):
        """Authenticate to the device."""
        try:
            await self.hass.async_add_executor_job(self.device.auth)
        except (BroadlinkException, OSError) as err:
            _LOGGER.debug(
                "Failed to authenticate to the device at %s: %s", self.device.host[0], err
            )
            return False
        return True

    @property
    def name(self): 
        return self._attr_name
    