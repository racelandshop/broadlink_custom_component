"""Support for Broadlink remotes."""

from time import time
from .const import DOMAIN
from .helpers import decode_packet

import asyncio
from base64 import b64encode, b64decode
from broadlink.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BroadlinkException,
    ConnectionClosedError,
    ReadError,
    StorageError,
    NetworkTimeoutError,
)
from datetime import timedelta
from functools import partial
from homeassistant.util import dt

import logging


_LOGGER = logging.getLogger(__name__)
LEARNING_TIMEOUT = timedelta(seconds=40)


class BroadlinkRemote():
    """Representation of a Broadlink remote (Not an entity)."""

    def __init__(self, hass, device, preset_list = {}):
        """Initialize the entity.
        Args:
        @hass: Homeassistant - The homeassistant object 
        @device: str - The device type
        @command_list: a dict of presets to be used by the entity. Each preset is a dictionary with the key being the name of the button and the value being the code to send."""
        
        self.hass  = hass
        self._device = device 
        self.preset_list = preset_list
        self.learning = False


    async def send_command(self, button_name, preset): 
        """Send a command with the button name"""
        code = self.preset_list[preset].get(button_name)
        if code is None:
            self.hass.components.persistent_notification.async_create(
                "Nennhum comando registado para o butão '{}'".format(button_name),
                title="Envio de comando",
                notification_id="send_command_missing",
                ) 
            return 
        try:
            code = decode_packet(code)
            await self.async_request(self._device.send_data, code)
        except (BroadlinkException, OSError) as err:
            _LOGGER.debug("Error during send_command: %s", err)


    async def learn_command(self, button_name, preset): 
        """Learn command from the device.
        Returns code to save in the storage"""
        self.learning = True
        try: 
            await self.async_request(self._device.enter_learning)
        except (BroadlinkException, OSError) as err:
            _LOGGER.debug("Failed to enter learning mode: %s", err)
            raise

        self.hass.components.persistent_notification.async_create(
           "Pressione um botão do seu dispositivo para ser aprendido por '{}'".format(self._device.type),
           title="Aprender comando",
           notification_id="learn_command",
        )
        code = None
        start_time = dt.utcnow()
        while (dt.utcnow() - start_time) < LEARNING_TIMEOUT:
            await asyncio.sleep(1)
            try:
                code = await self.async_request(self._device.check_data)
            except (ReadError, StorageError):
                continue
            
            decoded_code = b64encode(code).decode("utf8")
            self.preset_list[preset][button_name] = decoded_code

            self.hass.components.persistent_notification.async_dismiss(
               notification_id="learn_command"
            )
            self.learning = False
            return decoded_code
       

        _LOGGER.debug("Learn command timed out")
        self.hass.components.persistent_notification.async_create(
            "O dispositivo {} não capturou nenhum comando. Tente novamente".format(self._device.type),
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
            await self.hass.async_add_executor_job(self._device.auth)
        except (BroadlinkException, OSError) as err:
            _LOGGER.debug(
                "Failed to authenticate to the device at %s: %s", self._device.host[0], err
            )
            return False
        return True
    
