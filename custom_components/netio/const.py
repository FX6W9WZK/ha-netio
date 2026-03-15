"""Constants for the NETIO integration."""

from __future__ import annotations

DOMAIN = "netio"

CONF_DEVICE_URL = "device_url"

# Default JSON API credentials per NETIO documentation
DEFAULT_USERNAME = "netio"
DEFAULT_PASSWORD = "netio"
DEFAULT_SCAN_INTERVAL = 30  # seconds

# NETIO JSON API endpoint
NETIO_JSON_ENDPOINT = "/netio.json"

# NETIO output actions (from JSON API Protocol docs)
ACTION_OFF = 0
ACTION_ON = 1
ACTION_SHORT_OFF = 2
ACTION_SHORT_ON = 3
ACTION_TOGGLE = 4
ACTION_NO_CHANGE = 5
ACTION_IGNORED = 6

# NETIO output states
STATE_OUTPUT_OFF = 0
STATE_OUTPUT_ON = 1

# Options flow: enable/disable button entity types
CONF_ENABLE_RESTART = "enable_restart"
CONF_ENABLE_SHORT_ON = "enable_short_on"
CONF_ENABLE_TOGGLE = "enable_toggle"

# Supported device models from NETIO documentation
# Current products (from netio-products.com/en/products/all-products)
# Obsolete products (from netio-products.com/en/products/obsolete-products)
#
# Energy metering available on (per JSON API doc):
#   PowerPDU 4C, PowerCable REST 101x, PowerBOX 4Kx,
#   PowerDIN 4PZ, PowerPDU 8QS
#
# No metering:
#   PowerBOX 3Px, PowerPDU 4PS, NETIO 4 (obsolete)
#
# The integration auto-detects metering support from the JSON response.
