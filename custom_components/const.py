"""Cost for broadlink custom card integration"""
from homeassistant.const import Platform

DOMAINS_AND_TYPES = {
    Platform.REMOTE: {"RM4MINI", "RM4PRO", "RMMINI", "RMMINIB", "RMPRO"},
    Platform.SENSOR: {
        "A1",
        "RM4MINI",
        "RM4PRO",
        "RMPRO",
        "SP2S",
        "SP3S",
        "SP4",
        "SP4B",
    },  
    Platform.SWITCH: {
        "BG1",
        "MP1",
        "RM4MINI",
        "RM4PRO",
        "RMMINI",
        "RMMINIB",
        "RMPRO",
        "SP1",
        "SP2",
        "SP2S",
        "SP3",
        "SP3S",
        "SP4",
        "SP4B",
    },
    Platform.LIGHT: {"LB1"}
}


TIMEOUT = 5
DOMAIN = "broadlink_custom_card"
DEVICE_INFO  = "devices_info"
COMMANDS = "commands"
MAC = "mac"
DEVICE_MAC = "device_mac"
DEVICE_TYPE = "device_type"
DEVICE_JSON = "devices_storage"
PRESETS = "presets"
ACTIVE = "active"