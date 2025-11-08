"""Constants for the OpenKarotz integration."""
import logging
from typing import Final

DOMAIN: Final = "openkarotz"
LOGGER = logging.getLogger(__package__)

# Intervalle de polling pour le coordinateur (basé sur Doc 2)
# 30 secondes est un bon compromis
COORDINATOR_POLL_INTERVAL: Final = 30