"""Helpers for the Broadlink remote."""

from base64 import b64decode

from homeassistant.helpers import config_validation as cv

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