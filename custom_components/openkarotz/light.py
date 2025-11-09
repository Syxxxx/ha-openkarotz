"""Light platform for OpenKarotz."""
from homeassistant.components.light import (
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
    ATTR_FLASH,
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
    """

    _attr_has_entity_name = True
    _attr_name = "LED"
    _attr_supported_color_modes = {ColorMode.RGB}
    # --- SIMPLIFIÉ : Ne supporte plus que le flash simple (on/off) ---
    _attr_supported_features = LightEntityFeature.FLASH

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
    def color_mode(self) -> str | None:
        """Return the color mode of the light."""
        return ColorMode.RGB # Le mode est toujours RGB

    @property
    def is_on(self) -> bool:
        """Return true if the light is on (based on coordinator state)."""
        if not self.coordinator.data:
            return False
        color = self.coordinator.data.get("led_color", "000000")
        return color != "000000"

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value."""
        if not self.is_on or not self.coordinator.data:
            return None

        hex_color = self.coordinator.data.get("led_color", "000000")
        try:
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except (ValueError, TypeError):
            return None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        rgb: tuple[int, int, int] | None = kwargs.get(ATTR_RGB_COLOR)

        # 1. Déterminer la couleur
        if rgb is None:
            if self.is_on and self.rgb_color:
                rgb = self.rgb_color
            else:
                rgb = (255, 255, 255) # Blanc par défaut

        color_hex = f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        
        # 2. Déterminer le clignotement
        # Si le flash est demandé, on utilise la vitesse "normale"
        # Le sélecteur 'select.karotz_led_effect' est maintenant le
        # seul moyen de contrôler la vitesse.
        pulse = False
        speed = None
        
        if kwargs.get(ATTR_FLASH) is not None:
            pulse = True
            speed = 700 # Vitesse normale pour le flash simple

        # 3. Appeler l'API
        if await self._client.async_set_led(color=color_hex, pulse=pulse, speed=speed):
            self._update_local_data(color_hex, pulse=pulse)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        if await self._client.async_set_led(color="000000"):
            self._update_local_data("000000", pulse=False)

    @callback
    def _update_local_data(self, color_hex: str, pulse: bool) -> None:
        """Optimistically update the coordinator's data and HA state."""
        if self.coordinator.data:
            self.coordinator.data["led_color"] = color_hex
            self.coordinator.data["led_pulse"] = "1" if pulse else "0"
        self.async_write_ha_state()
        self.hass.loop.create_task(self.coordinator.async_request_refresh())