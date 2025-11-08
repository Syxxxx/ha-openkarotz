"""Media player platform for OpenKarotz."""
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import KarotzApiClient
from .const import DOMAIN

# Fonctionnalités supportées
SUPPORT_KAROTZ = (
    MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the media player platform."""
    client: KarotzApiClient = hass.data[DOMAIN][entry.entry_id]["client"]
    async_add_entities([KarotzMediaPlayer(client, entry)])


class KarotzMediaPlayer(MediaPlayerEntity):
    """Representation of the Karotz media player."""

    _attr_has_entity_name = True
    _attr_name = "Lecteur"
    _attr_supported_features = SUPPORT_KAROTZ
    _attr_icon = "mdi:rabbit"
    
    # Cet appareil est "optimiste"
    _attr_should_poll = False 

    def __init__(self, client: KarotzApiClient, entry: ConfigEntry) -> None:
        """Initialize the media player."""
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