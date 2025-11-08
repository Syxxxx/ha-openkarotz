"""Light platform for OpenKarotz."""
from homeassistant.components.light import (
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import KarotzApiClient
from .const import DOMAIN
from .coordinator import KarotzCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: KarotzCoordinator = data["coordinator"]
    client: KarotzApiClient = data["client"]
    
    async_add_entities([KarotzLight(coordinator, client, entry)])


class KarotzLight(CoordinatorEntity[KarotzCoordinator], LightEntity):
    """
    Representation of the Karotz LED, based on coordinator data.
    Cette entité n'est PAS optimiste (contrairement au Doc 1).
    """

    _attr_has_entity_name = True
    _attr_name = "LED"
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(
        self,
        coordinator: KarotzCoordinator,
        client: KarotzApiClient,
        entry: ConfigEntry
    ):
        """Initialize the light."""
        super().__init__(coordinator)
        self._client = client
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_led"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
        )

    @property
    def is_on(self) -> bool:
        """Return true if the light is on (based on coordinator state)."""
        if not self.coordinator.data:
            return False
        # L'état est "on" si la couleur n'est pas "000000" (éteint)
        color = self.coordinator.data.get("led_color", "000000")
        return color != "000000"

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value."""
        if not self.is_on or not self.coordinator.data:
            return None

        hex_color = self.coordinator.data.get("led_color", "000000")
        try:
            # Convertir la chaîne hexadécimale (ex: "FF00AA") en tuple RGB
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except (ValueError, TypeError):
            return None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        rgb: tuple[int, int, int] | None = kwargs.get(ATTR_RGB_COLOR)
        
        if rgb is None:
            rgb = (255, 255, 255) # Blanc par défaut si aucune couleur n'est fournie

        # Convertir le tuple RGB en chaîne hexadécimale
        color_hex = f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        
        if await self._client.async_set_led(color=color_hex):
            # Pour une meilleure réactivité de l'interface, nous mettons à jour l'état
            # localement AVANT le prochain poll du coordinateur.
            self._update_local_data(color_hex)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        if await self._client.async_set_led(color="000000"):
            self._update_local_data("000000")

    @callback
    def _update_local_data(self, color_hex: str) -> None:
        """Optimistically update the coordinator's data and HA state."""
        if self.coordinator.data:
            self.coordinator.data["led_color"] = color_hex
        self.async_write_state()
        # Demande un rafraîchissement au coordinateur pour confirmer l'état.
        self.hass.loop.create_task(self.coordinator.async_request_refresh())