"""Sensor platform for OpenKarotz to display the webhook URL."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.webhook import get_webhook_url

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities([KarotzWebhookSensor(hass, entry)])


class KarotzWebhookSensor(SensorEntity):
    """Exposes the unique webhook URL for the Karotz."""

    _attr_has_entity_name = True
    _attr_name = "Webhook URL"
    _attr_icon = "mdi:webhook"
    
    # Désactivé par défaut, car c'est un outil de diagnostic/setup
    _attr_entity_registry_enabled_default = False 

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_webhook_url"
        
        # Récupérer l'ID généré lors du setup dans __init__.py
        webhook_id = hass.data[DOMAIN][entry.entry_id].get("webhook_id")
        
        # Construire l'URL complète que le Karotz doit appeler
        self._attr_native_value = get_webhook_url(hass, webhook_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
        )