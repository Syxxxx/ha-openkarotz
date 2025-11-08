"""Cover platform for OpenKarotz (Ears)."""
import math
from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
    CoverDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import KarotzApiClient
from .const import DOMAIN

# L'API Karotz va de 0 (bas) à 16 (haut)
KAROTZ_MIN_POS = 0
KAROTZ_MAX_POS = 16

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover platform."""
    client: KarotzApiClient = hass.data[DOMAIN][entry.entry_id]["client"]
    async_add_entities([KarotzEars(client, entry)])


class KarotzEars(CoverEntity):
    """Representation of the Karotz ears as a cover."""

    _attr_has_entity_name = True
    _attr_name = "Oreilles"
    _attr_device_class = CoverDeviceClass.AWNING
    _attr_icon = "mdi:rabbit"
    _attr_supported_features = (
        CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
    )

    def __init__(self, client: KarotzApiClient, entry: ConfigEntry) -> None:
        """Initialize the cover."""
        self._client = client
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_ears"
        
        # État optimiste (on suppose 50% au démarrage)
        self._attr_current_cover_position = 50
        self._attr_is_closed = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
        )

    def _ha_to_karotz_pos(self, ha_pos: int) -> int:
        """Convert HA position (0-100) to Karotz position (0-16)."""
        percentage = ha_pos / 100
        karotz_pos = math.floor(percentage * KAROTZ_MAX_POS)
        return karotz_pos

    async def async_set_cover_position(self, **kwargs) -> None:
        """Set the ear position."""
        position = kwargs["position"]
        karotz_pos = self._ha_to_karotz_pos(position)
        
        if await self._client.async_set_ears(karotz_pos, karotz_pos):
            self._attr_current_cover_position = position
            self._attr_is_closed = position == 0
            self.async_write_state()

    async def async_open_cover(self, **kwargs) -> None:
        """Open the ears (position 100)."""
        await self.async_set_cover_position(position=100)

    async def async_close_cover(self, **kwargs) -> None:
        """Close the ears (position 0)."""
        await self.async_set_cover_position(position=0)