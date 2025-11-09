"""Switch platform for OpenKarotz (Sleep/Wake)."""
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
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
    """Set up the switch platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: KarotzCoordinator = data["coordinator"]
    client: KarotzApiClient = data["client"]
    
    async_add_entities([KarotzSleepSwitch(coordinator, client, entry)])


class KarotzSleepSwitch(CoordinatorEntity[KarotzCoordinator], SwitchEntity):
    """Representation of the Karotz sleep switch."""

    _attr_has_entity_name = True
    _attr_name = "Veille"
    _attr_icon = "mdi:power-sleep"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        coordinator: KarotzCoordinator,
        client: KarotzApiClient,
        entry: ConfigEntry
    ):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._client = client
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sleep_switch"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
        )

    @property
    def is_on(self) -> bool:
        """Return true if the device is sleeping (switch is ON)."""
        if not self.coordinator.data:
            return False
        # "on" (endormi) si "sleep" == "1"
        return self.coordinator.data.get("sleep") == "1"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on (put Karotz to sleep)."""
        if await self._client.async_sleep():
            self._update_local_data("1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off (wake up Karotz)."""
        if await self._client.async_wakeup():
            self._update_local_data("0")

    @callback
    def _update_local_data(self, sleep_state: str) -> None:
        """Optimistically update the coordinator's data and HA state."""
        if self.coordinator.data:
            self.coordinator.data["sleep"] = sleep_state
        self.async_write_state()
        # Demande un rafraîchissement pour confirmer l'état.
        self.hass.loop.create_task(self.coordinator.async_request_refresh())