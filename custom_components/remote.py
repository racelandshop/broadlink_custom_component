"""Support for Broadlink remotes."""

from time import time
from timeit import default_timer
from .const import COMMANDS, DOMAIN
from .helpers import decode_packet

import asyncio
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
from homeassistant.util import dt

import logging


_LOGGER = logging.getLogger(__name__)

LEARNING_TIMEOUT_RMPRO = timedelta(seconds=30)
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
        self.learningTimeout = LEARNING_TIMEOUT_RMPRO if isinstance(self._device, rmpro) else LEARNING_TIMEOUT

    async def send_command(self, button_name, preset): 
        """Send a command with the button name"""
        code = self.preset_list[preset][COMMANDS].get(button_name)
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
        """"Learn a command from the device. Updates the self.learning state of the instance. 
        self.learning acts as a lock to prevent the learning process to co-occur"""
        self.learning = True
        try: 
            return await self._learn_command(button_name, preset)
        except (BroadlinkException, OSError) as err:
            raise
        finally: 
            self.learning = False


    async def _learn_command(self, button_name, preset): 
        """Learn command from the device.
        Returns code"""
        try: 
            await self.async_request(self._device.enter_learning)
        except (BroadlinkException, OSError) as err:
            self.learning = False
            self.hass.components.persistent_notification.async_create(f"Erro ao entrar em modo de aprendizagem. Verifique que comando universal da broadlink ({self._device.type}) está conectada", 
                title="Erro", notification_id="learn_command_error")
            raise

        self.hass.components.persistent_notification.async_create(
           f"Pressione um botão do seu dispositivo para ser aprendido por {self._device.type}",
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
            print("PRESET", preset)
            print("[!] preset_list", self.preset_list)
            self.preset_list[preset][COMMANDS][button_name] = decoded_code

            self.hass.components.persistent_notification.async_dismiss(
               notification_id="learn_command"
            )
            return decoded_code

        if isinstance(self._device, rmpro): 
            self.async_request(self._device.cancel_sweep_frequency)

        self.hass.components.persistent_notification.async_create(
            f"O dispositivo {self._device.type} não capturou nenhum comando. Tente novamente",
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
    