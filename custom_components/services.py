"""Setup custom broadlink remote services"""
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv

import voluptuous as vol
import logging

_LOGGER = logging.getLogger(__name__)


SERVICE_SEND_COMMAND = "send_command"
ATTR_BUTTON_NAME = "button_name"


async def setup_services():
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SEND_COMMAND,
        {
            vol.Optional(ATTR_BUTTON_NAME): cv.string,
        },
        "async_send_command",
    )


