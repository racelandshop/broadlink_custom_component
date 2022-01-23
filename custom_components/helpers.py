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


#TODO: not used, implement later as I'm using these in the code indirectly
# def mac_address(mac):
#     """Validate and convert a MAC address to bytes."""
#     mac = cv.string(mac)
#     if len(mac) == 17:
#         mac = "".join(mac[i : i + 2] for i in range(0, 17, 3))
#     elif len(mac) == 14:
#         mac = "".join(mac[i : i + 4] for i in range(0, 14, 5))
#     elif len(mac) != 12:
#         raise ValueError("Invalid MAC address")
#     return bytes.fromhex(mac)


def format_mac(mac):
    """Format a MAC address."""
    return ":".join([format(octet, "02x") for octet in mac])
