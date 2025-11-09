"""The OpenKarotz integration."""
from __future__ import annotations

import aiohttp.web
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import CONF_HOST, Platform
from homeassistant.helpers import device_registry as dr
# LIGNES MODIFIÉES
from homeassistant.components.webhook import (
    async_generate_id,
    async_register,
    async_unregister,
)
from homeassistant.helpers.typing import ConfigType

from .api import KarotzApiClient
from .coordinator import KarotzCoordinator
from .const import DOMAIN, LOGGER

# Plateformes à charger
PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.MEDIA_PLAYER,
    Platform.COVER,
    Platform.CAMERA,
    Platform.BINARY_SENSOR, # Pour le statut "Veille"
    Platform.SENSOR,         # Pour l'URL du Webhook
]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the OpenKarotz component."""
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["webhooks"] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenKarotz from a config entry."""
    
    host = entry.data[CONF_HOST]

    # 1. Créer le Client API et le Coordinateur d'état
    client = KarotzApiClient(hass, host)
    coordinator = KarotzCoordinator(hass, client)

    # 2. Premier rafraîchissement (lit /cgi-bin/status)
    # Cela valide aussi la connexion avant de continuer.
    await coordinator.async_config_entry_first_refresh()

    # 3. Enregistrer le Webhook "push"
    # LIGNE MODIFIÉE (suppression de 'webhook.')
    webhook_id = async_generate_id()
    try:
        # LIGNE MODIFIÉE (suppression de 'webhook.')
        async_register(
            hass,
            DOMAIN,
            "OpenKarotz Events",
            webhook_id,
            handle_webhook,
        )
        LOGGER.info("Webhook %s enregistré pour Karotz (%s)", webhook_id, entry.title)
    except ValueError:
        LOGGER.error("Impossible d'enregistrer le webhook %s, il existe déjà.", webhook_id)
        return False

    # 4. Stocker les objets pour les entités
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "webhook_id": webhook_id,
    }
    
    # 5. Stocker le mapping Webhook -> Entry
    hass.data[DOMAIN]["webhooks"][webhook_id] = entry.entry_id

    # 6. Créer l'appareil dans le registre
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="OpenKarotz",
        model="Karotz",
    )

    # 7. Charger les plateformes (light, camera, etc.)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # 1. Décharger les plateformes
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    # 2. Désenregistrer le Webhook
    data = hass.data[DOMAIN][entry.entry_id]
    webhook_id = data.get("webhook_id")
    if webhook_id:
        try:
            # LIGNE MODIFIÉE (suppression de 'webhook.')
            async_unregister(hass, webhook_id)
            LOGGER.info("Webhook %s désenregistré.", webhook_id)
        except ValueError:
            LOGGER.warning("Webhook %s déjà désenregistré.", webhook_id)
        
        # Nettoyer le mapping
        hass.data[DOMAIN]["webhooks"].pop(webhook_id, None)

    # 3. Nettoyer hass.data
    hass.data[DOMAIN].pop(entry.entry_id)

    return True

@callback
async def handle_webhook(
    hass: HomeAssistant, webhook_id: str, request: aiohttp.web.Request
) -> aiohttp.web.Response:
    """Handle incoming webhook from Karotz dbus_watcher."""
    
    # 1. Trouver l'appareil (entry_id) qui correspond à ce webhook
    entry_id = hass.data[DOMAIN]["webhooks"].get(webhook_id)
    if not entry_id:
        LOGGER.warning("Webhook reçu pour un ID inconnu: %s", webhook_id)
        return aiohttp.web.Response(status=404, text="Webhook ID not found")

    # 2. Récupérer l'appareil HA
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry_id)})
    if not device:
        LOGGER.warning("Webhook %s reçu mais l'appareil n'est pas trouvé.", webhook_id)
        return aiohttp.web.Response(status=404, text="Device not found")

    # 3. Parser le JSON (POST)
    try:
        data = await request.json()
        event_type = data.get("event_type")
        LOGGER.debug("Webhook reçu de %s: %s", device.name, data)
    except Exception as err:
        LOGGER.warning("Erreur de parsing JSON du webhook Karotz: %s", err)
        return aiohttp.web.Response(status=400, text="Invalid JSON")

    # 4. Traiter l'événement
    if event_type == "rfid":
        tag_id = data.get("rfid_id")
        if not tag_id:
            LOGGER.warning("Événement RFID reçu sans 'rfid_id'")
            return aiohttp.web.Response(status=400, text="Missing rfid_id")
            
        LOGGER.info("Scan RFID natif reçu de %s, tag: %s", device.name, tag_id)
        
        # === C'est ici qu'on s'intègre au système RFID natif de HA ===
        hass.bus.async_fire(
            "tag_scanned",
            {"tag_id": tag_id, "device_id": device.id},
        )
        
    elif event_type == "button":
        event = data.get("event") # ex: "click", "dclick", "lclick_start"
        if not event:
            LOGGER.warning("Événement Bouton reçu sans 'event'")
            return aiohttp.web.Response(status=400, text="Missing event")
            
        LOGGER.info("Événement Bouton reçu de %s: %s", device.name, event)
        
        # === C'est ici qu'on déclenche l'événement pour les automations ===
        # Cet événement sera attrapé par device_trigger.py
        hass.bus.async_fire(
            f"{DOMAIN}_event",
            {
                "device_id": device.id,
                "type": event,
            },
        )
    else:
        LOGGER.warning("Webhook reçu avec event_type inconnu: %s", event_type)
        return aiohttp.web.Response(status=400, text="Unknown event_type")

    return aiohttp.web.Response(status=200, text="OK")