"""Select platform for OpenKarotz (LED Effect)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import KarotzApiClient
from .const import DOMAIN
from .coordinator import KarotzCoordinator

# Définition des effets de vitesse
KAROTZ_EFFECT_LIST = ["none", "pulse_fast", "pulse_normal", "pulse_slow"]

KAROTZ_SPEED_MAP = {
    "pulse_fast": 300,
    "pulse_normal": 700,
    "pulse_slow": 1500,
}

ENTITY_DESCRIPTION = SelectEntityDescription(
    key="led_effect",
    name="Effet LED",
    icon="mdi:light-replicate",
    options=KAROTZ_EFFECT_LIST,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: KarotzCoordinator = data["coordinator"]
    client: KarotzApiClient = data["client"]
    
    async_add_entities([KarotzLedEffectSelect(coordinator, client, entry, ENTITY_DESCRIPTION)])


class KarotzLedEffectSelect(CoordinatorEntity[KarotzCoordinator], SelectEntity):
    """Representation of the Karotz LED effect select."""

    _attr_has_entity_name = True
    _attr_current_option: str | None = "none" # État optimiste

    def __init__(
        self,
        coordinator: KarotzCoordinator,
        client: KarotzApiClient,
        entry: ConfigEntry,
        description: SelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._client = client
        self._entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
        )

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the state."""
        # Si le coordinateur dit que la LED ne clignote pas,
        # on force l'état du sélecteur à "none".
        if self.coordinator.data and self.coordinator.data.get("led_pulse") == "0":
            self._attr_current_option = "none"
            return "none"
        
        # Sinon, on se fie à notre état optimiste
        return self._attr_current_option

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self.entity_description.options:
            raise ValueError(f"Option invalide: {option}")

        # Récupérer la couleur actuelle depuis le coordinateur
        current_color = "00FF00" # Vert par défaut si inconnu
        if self.coordinator.data:
            current_color = self.coordinator.data.get("led_color", "00FF00")
            # Si la LED est éteinte, on la met en vert
            if current_color == "000000":
                current_color = "00FF00"

        pulse = False
        speed = None

        if option != "none":
            pulse = True
            speed = KAROTZ_SPEED_MAP.get(option, 700)
        
        # Appeler l'API avec la couleur actuelle et le nouvel effet
        if await self._client.async_set_led(color=current_color, pulse=pulse, speed=speed):
            # Mettre à jour l'état optimiste et le coordinateur
            self._attr_current_option = option
            if self.coordinator.data:
                self.coordinator.data["led_pulse"] = "1" if pulse else "0"
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()