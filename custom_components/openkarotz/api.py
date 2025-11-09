"""API Client for OpenKarotz."""
import aiohttp
from typing import Any
import json

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

from .const import LOGGER

class KarotzApiClient:
    """Asynchronous client for the OpenKarotz cgi-bin API."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize the API client."""
        self._host = host
        self._base_url = f"http://{self._host}/cgi-bin"
        self._session = async_get_clientsession(hass)
        self._snapshot_error_logged = False # Garder le drapeau anti-spam

    async def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> bool:
        """Make a GET request to a cgi-bin ACTION endpoint."""
        url = f"{self._base_url}/{endpoint}"
        
        try:
            async with self._session.get(url, params=params, timeout=10) as response:
                response.raise_for_status() # Lève une exception pour 4xx/5xx
                
                # Les actions (leds, tts) renvoient du JSON avec un content-type
                # incorrect, mais contiennent une clé "return".
                data = await response.json(content_type=None)
                
                if data and data.get("return") == "0":
                    LOGGER.debug("Action %s réussie", endpoint)
                    return True
                
                msg = data.get("msg")
                if endpoint == "sound_control" and msg == "No sound currently playing.":
                    LOGGER.debug("Action sound_control échouée (normal): %s", msg)
                else:
                    LOGGER.warning("Action %s échouée (API error): %s", endpoint, data)
                
                return False

        except aiohttp.ClientConnectorError:
            LOGGER.error("Échec de connexion au Karotz à %s", self._host)
            raise ConnectionError(f"Cannot connect to Karotz at {self._host}")
        except aiohttp.ClientError as err:
            LOGGER.warning("Erreur API Karotz (%s): %s", endpoint, err)
            return False
        except Exception as err:
            LOGGER.error("Erreur inattendue API Karotz (%s): %s", endpoint, err)
            return False

    async def async_get_status(self) -> dict[str, Any] | None:
        """Get the device status (from /cgi-bin/status). This endpoint is special."""
        url = f"{self._base_url}/status"
        try:
            async with self._session.get(url, timeout=10) as response:
                response.raise_for_status()
                # Lire le texte brut (car Content-Type=text/plain) et parser manuellement
                raw_data = await response.text()
                data = json.loads(raw_data)
                # /status n'a pas de clé "return", on renvoie juste les données
                return data
        except (aiohttp.ClientError, json.JSONDecodeError, ConnectionError) as err:
            LOGGER.warning("Impossible de récupérer le statut du Karotz: %s", err)
            # Re-lever l'erreur pour que le coordinateur la gère comme un échec
            raise ConnectionError(f"Failed to get status: {err}") from err

    async def async_set_led(
        self,
        color: str,
        color2: str | None = None,
        pulse: bool = False,
        speed: int | None = None
    ) -> bool:
        """Set the LED color and behavior."""
        params = {
            "color": color,
            "pulse": "1" if pulse else "0",
            "no_memory": "1", # Ne pas mémoriser est plus sûr pour HA
        }
        if color2:
            params["color2"] = color2
        if speed:
            params["speed"] = speed
            
        return await self._request("leds", params)

    async def async_tts(self, text: str, voice: str = "claire") -> bool:
        """Send a Text-to-Speech message."""
        params = {"text": text, "voice": voice, "nocache": "1"}
        return await self._request("tts", params)

    async def async_play_sound(self, url: str) -> bool:
        """Play a sound from a URL."""
        params = {"url": url}
        return await self._request("sound", params)

    async def async_sound_control(self, cmd: str) -> bool:
        """Control sound playback (pause or quit)."""
        params = {"cmd": cmd}
        return await self._request("sound_control", params)

    async def async_set_ears(self, left: int, right: int) -> bool:
        """Set ear positions."""
        # Note: L'API attend les positions de 0 (bas) à 16 (haut)
        params = {"left": left, "right": right, "no_memory": "1"}
        return await self._request("ears", params)

    async def async_ears_random(self) -> bool:
        """Move ears randomly."""
        return await self._request("ears_random")
        
    async def async_sleep(self) -> bool:
        """Put the Karotz to sleep."""
        return await self._request("sleep")
        
    async def async_wakeup(self) -> bool:
        """Wake up the Karotz."""
        return await self._request("wakeup", {"silent": "1"})

    async def async_get_snapshot(self) -> bytes | None:
        """Get a camera snapshot."""
        url = f"{self._base_url}/snapshot_view?silent=1"
        
        # --- MODIFICATION : En-têtes minimaux pour imiter curl ---
        headers = {
            "Accept": "image/jpeg, */*",
            "Accept-Encoding": "identity" # Demander de ne PAS compresser
        }
        
        try:
            # Ajout de headers=headers
            async with self._session.get(url, timeout=5, headers=headers) as response:
                response.raise_for_status()
                data = await response.read()
                # Si la lecture réussit, on réinitialise le drapeau
                self._snapshot_error_logged = False
                return data
        except aiohttp.ClientError as err:
            if not self._snapshot_error_logged:
                LOGGER.warning("Impossible de récupérer le snapshot de la caméra (le script /cgi-bin/snapshot_view est peut-être cassé sur le Karotz): %s", err)
                self._snapshot_error_logged = True
            else:
                LOGGER.debug("Erreur snapshot (déjà signalée): %s", err)
            return None
        except Exception as err:
            if not self._snapshot_error_logged:
                LOGGER.error("Erreur inattendue snapshot: %s", err)
                self._snapshot_error_logged = True
            return None

    async def async_set_volume(self, volume: int) -> bool:
        """Set the volume (0-20)."""
        # L'API OpenKarotz documente cmd=vol&v=X (où X est 0-20)
        params = {"cmd": "vol", "v": volume}
        return await self._request("sound_control", params)

    async def async_volume_up(self) -> bool:
        """Turn volume up by one step."""
        params = {"cmd": "volup"}
        return await self._request("sound_control", params)

    async def async_volume_down(self) -> bool:
        """Turn volume down by one step."""
        params = {"cmd": "voldown"}
        return await self._request("sound_control", params)

    async def async_play_mood(self, mood_id: int) -> bool:
        """Play a mood by ID."""
        params = {"id": mood_id}
        return await self._request("moods", params)

    async def async_play_sound_local(self, sound_id: str) -> bool:
        """Play a local sound by ID (filename)."""
        params = {"id": sound_id}
        return await self._request("sound", params)

    async def async_play_radio(self, radio_id: int) -> bool:
        """Play a preset radio by ID."""
        params = {"id": radio_id}
        return await self._request("radio", params)