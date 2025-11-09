"""Sensor platform for OpenKarotz."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.webhook import async_generate_url
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KarotzCoordinator

# --- NOUVEAU : Description des capteurs de diagnostic ---
# Basés sur les clés de /cgi-bin/status
DIAGNOSTIC_SENSORS: tuple[tuple[str, str, str, str | None, str | None, str | None], ...] = (
    (
        "version",
        "Version Firmware",
        "mdi:chip",
        None,
        None,
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "wlan_mac",
        "Adresse MAC",
        "mdi:network-outline",
        None,
        None,
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "karotz_free_space",
        "Espace disque",
        "mdi:harddisk",
        None, # L'API renvoie "149.5M", donc pas un nombre simple
        None,
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "karotz_percent_used_space",
        "Espace disque utilisé",
        "mdi:harddisk",
        PERCENTAGE,
        SensorStateClass.MEASUREMENT,
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "nb_tags",
        "Tags RFID",
        "mdi:rfid",
        None,
        SensorStateClass.MEASUREMENT,
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "nb_moods",
        "Humeurs",
        "mdi:emoticon-happy-outline",
        None,
        SensorStateClass.MEASUREMENT,
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "nb_sounds",
        "Sons",
        "mdi:music-note",
        None,
        SensorStateClass.MEASUREMENT,
        EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: KarotzCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    # Créer la liste des entités
    entities = [
        # Le capteur Webhook, qui est unique
        KarotzWebhookSensor(hass, entry)
    ]
    
    # Ajouter tous les capteurs de diagnostic
    for key, name, icon, unit, state_class, category in DIAGNOSTIC_SENSORS:
        entities.append(
            KarotzDiagnosticSensor(
                coordinator,
                entry,
                key,
                name,
                icon,
                unit,
                state_class,
                category,
            )
        )
        
    async_add_entities(entities)


class KarotzWebhookSensor(SensorEntity):
    """Exposes the unique webhook URL for the Karotz."""

    _attr_has_entity_name = True
    _attr_name = "Webhook URL"
    _attr_icon = "mdi:webhook"
    
    # Désactivé par défaut, car c'est un outil de diagnostic/setup
    _attr_entity_registry_enabled_default = False 
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_webhook_url"
        
        # Récupérer l'ID généré lors du setup dans __init__.py
        webhook_id = hass.data[DOMAIN][entry.entry_id].get("webhook_id")
        
        # Construire l'URL complète que le Karotz doit appeler
        self._attr_native_value = async_generate_url(hass, webhook_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
        )


class KarotzDiagnosticSensor(CoordinatorEntity[KarotzCoordinator], SensorEntity):
    """Representation of a Karotz diagnostic sensor."""

    _attr_has_entity_name = True
    
    # Ces capteurs sont désactivés par défaut
    _attr_entity_registry_enabled_default = False 

    def __init__(
        self,
        coordinator: KarotzCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        icon: str,
        unit: str | None,
        state_class: str | None,
        category: str | None,
    ) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr_entity_category = category

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
        )

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._key)