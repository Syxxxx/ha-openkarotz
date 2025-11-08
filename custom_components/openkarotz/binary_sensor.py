"""Binary sensor platform for OpenKarotz."""
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KarotzCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator: KarotzCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([KarotzSleepSensor(coordinator, entry)])


class KarotzSleepSensor(CoordinatorEntity[KarotzCoordinator], BinarySensorEntity):
    """Representation of the Karotz sleep status."""

    _attr_has_entity_name = True
    _attr_name = "Veille"
    _attr_device_class = BinarySensorDeviceClass.SLEEPING # Donne la bonne icône

    def __init__(
        self,
        coordinator: KarotzCoordinator,
        entry: ConfigEntry
    ):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sleep_status"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
        )

    @property
    def is_on(self) -> bool:
        """Return true if the device is sleeping."""
        if not self.coordinator.data:
            return False
        # L'API (Doc 2) indique que "1" = endormi, "0" = réveillé
        return self.coordinator.data.get("sleep") == "1"