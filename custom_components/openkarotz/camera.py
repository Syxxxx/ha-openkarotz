"""Camera platform for OpenKarotz."""
from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import KarotzApiClient
from .const import DOMAIN, LOGGER

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the camera platform."""
    client: KarotzApiClient = hass.data[DOMAIN][entry.entry_id]["client"]
    async_add_entities([KarotzCamera(client, entry)])


class KarotzCamera(Camera):
    """Representation of the Karotz camera."""

    _attr_has_entity_name = True
    _attr_name = "Caméra"
    _attr_supported_features = CameraEntityFeature(0) # Pas de streaming

    def __init__(self, client: KarotzApiClient, entry: ConfigEntry) -> None:
        """Initialize the camera."""
        super().__init__()
        self._client = client
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_camera"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
        )

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a snapshot image from the camera."""
        try:
            return await self._client.async_get_snapshot()
        except Exception as err:
            LOGGER.error("Erreur lors de la récupération du snapshot: %s", err)
            return None