"""Media player platform for OpenKarotz."""
import voluptuous as vol
import math
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity # <-- IMPORT AJOUTÉ
from homeassistant.helpers import entity_platform, config_validation as cv

from .api import KarotzApiClient
from .const import DOMAIN, LOGGER
from .coordinator import KarotzCoordinator # Importé pour lire le volume

# --- NOUVELLES FONCTIONNALITÉS (basées sur Jeedom) ---
# L'API OpenKarotz a un volume de 0 à 20
KAROTZ_MIN_VOLUME = 0
KAROTZ_MAX_VOLUME = 20

# Fonctionnalités supportées (MISES À JOUR)
SUPPORT_KAROTZ = (
    MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_STEP
)

# Schémas pour les nouveaux services
SERVICE_PLAY_MOOD = {
    vol.Required("mood_id"): cv.positive_int,
}
SERVICE_PLAY_SOUND = {
    vol.Required("sound_id"): cv.string,
}
SERVICE_PLAY_RADIO = {
    vol.Required("radio_id"): cv.positive_int,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the media player platform."""
    client: KarotzApiClient = hass.data[DOMAIN][entry.entry_id]["client"]
    # Nous avons besoin du coordinateur pour lire le volume
    coordinator: KarotzCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    player = KarotzMediaPlayer(client, coordinator, entry)
    async_add_entities([player])

    # --- ENREGISTREMENT DES NOUVEAUX SERVICES ---
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "play_mood",
        SERVICE_PLAY_MOOD,
        player.async_service_play_mood,
    )
    platform.async_register_entity_service(
        "play_sound",
        SERVICE_PLAY_SOUND,
        player.async_service_play_sound,
    )
    platform.async_register_entity_service(
        "play_radio",
        SERVICE_PLAY_RADIO,
        player.async_service_play_radio,
    )


class KarotzMediaPlayer(CoordinatorEntity[KarotzCoordinator], MediaPlayerEntity):
    """Representation of the Karotz media player."""

    _attr_has_entity_name = True
    _attr_name = "Lecteur"
    _attr_supported_features = SUPPORT_KAROTZ
    _attr_icon = "mdi:rabbit"
    
    # Cet appareil est "optimiste" pour l'état de lecture,
    # mais lit le volume depuis le coordinateur
    _attr_should_poll = False 

    def __init__(
        self,
        client: KarotzApiClient,
        coordinator: KarotzCoordinator,
        entry: ConfigEntry
    ) -> None:
        """Initialize the media player."""
        # Lier au coordinateur pour le volume
        super().__init__(coordinator) 
        
        self._client = client
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_player"
        self._attr_state = MediaPlayerState.IDLE # État optimiste

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
        )
    
    # --- PROPRIÉTÉS DE VOLUME (lues depuis le coordinateur) ---

    @property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0..1)."""
        if not self.coordinator.data:
            return None
        try:
            # Lire le volume (0-20) depuis /cgi-bin/status
            karotz_vol = int(self.coordinator.data.get("volume", 10))
            # Convertir en échelle 0.0 - 1.0 pour HA
            return karotz_vol / KAROTZ_MAX_VOLUME
        except (ValueError, TypeError):
            return None

    # --- COMMANDES DE LECTURE (optimistes) ---

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs
    ) -> None:
        """Play media."""
        success = False
        
        # Gérer le service tts.say
        if media_type == "tts":
            success = await self._client.async_tts(text=media_id)
        
        # Gérer le service media_player.play_media (URL)
        elif media_type == MediaType.MUSIC or media_id.startswith("http"):
            success = await self._client.async_play_sound(url=media_id)
            
        else:
            self.hass.async_create_task(
                self._client.async_tts(f"Type de média {media_type} non supporté.")
            )

        if success:
            self._attr_state = MediaPlayerState.PLAYING
            self.async_write_state()

    async def async_media_pause(self) -> None:
        """Pause the media (toggle)."""
        if await self._client.async_sound_control(cmd="pause"):
            self._attr_state = MediaPlayerState.PAUSED
            self.async_write_state()

    async def async_media_stop(self) -> None:
        """Stop the media."""
        if await self._client.async_sound_control(cmd="quit"):
            self._attr_state = MediaPlayerState.IDLE
            self.async_write_state()
            
    # --- COMMANDES DE VOLUME (avec mise à jour optimiste) ---
            
    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        # Convertir le volume HA (0.0-1.0) en volume Karotz (0-20)
        karotz_vol = math.ceil(volume * KAROTZ_MAX_VOLUME)
        
        if await self._client.async_set_volume(karotz_vol):
            # Mettre à jour le coordinateur localement pour la réactivité
            if self.coordinator.data:
                self.coordinator.data["volume"] = str(karotz_vol)
                self.async_write_state()
                # Demander un rafraîchissement pour confirmer
                await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        if await self._client.async_volume_up():
            # Demander un rafraîchissement pour lire la nouvelle valeur
            await self.coordinator.async_request_refresh()

    async def async_volume_down(self) -> None:
        """Volume down media player."""
        if await self._client.async_volume_down():
            # Demander un rafraîchissement pour lire la nouvelle valeur
            await self.coordinator.async_request_refresh()

    # --- GESTIONNAIRES DE SERVICES PERSONNALISÉS ---

    async def async_service_play_mood(self, mood_id: int) -> None:
        """Service call to play a mood."""
        LOGGER.info("Appel du service play_mood, ID: %s", mood_id)
        if await self._client.async_play_mood(mood_id):
            self._attr_state = MediaPlayerState.PLAYING
            self.async_write_state()

    async def async_service_play_sound(self, sound_id: str) -> None:
        """Service call to play a local sound."""
        LOGGER.info("Appel du service play_sound, ID: %s", sound_id)
        if await self._client.async_play_sound_local(sound_id):
            self._attr_state = MediaPlayerState.PLAYING
            self.async_write_state()

    async def async_service_play_radio(self, radio_id: int) -> None:
        """Service call to play a radio."""
        LOGGER.info("Appel du service play_radio, ID: %s", radio_id)
        if await self._client.async_play_radio(radio_id):
            self._attr_state = MediaPlayerState.PLAYING
            self.async_write_state()