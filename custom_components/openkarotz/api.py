"""API Client for OpenKarotz."""
import aiohttp
from typing import Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

from .const import LOGGER

class KarotzApiClient:
    """Asynchronous client for the OpenKarotz cgi-bin API."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize the API client."""
        self._host = host
        self._base_url = f"http://{self_host}/cgi-bin"
        self._session = async_get_clientsession(hass)

    async def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Make a GET request to a cgi-bin endpoint."""
        url = f"{self._base_url}/{endpoint}"
        
        try:
            async with self._session.get(url, params=params, timeout=10) as response:
                response.raise_for_status() # Lève une exception pour 4xx/5xx
                
                # L'API OpenKarotz retourne du JSON avec un content-type "text/html"
                # Nous forçons donc la lecture en JSON.
                data = await response.json(content_type=None)
                
                if data and data.get("return") == "0":
                    LOGGER.debug("Requête vers %s réussie: %s", url, data)
                    return data
                
                LOGGER.warning("Requête vers %s échouée (API error): %s", url, data)
                return None

        except aiohttp.ClientConnectorError:
            LOGGER.error("Échec de connexion au Karotz à %s", self._host)
            raise ConnectionError(f"Cannot connect to Karotz at {self._host}")
        except aiohttp.ClientError as err:
            LOGGER.warning("Erreur API Karotz: %s", err)
            return None
        except Exception as err:
            LOGGER.error("Erreur inattendue API Karotse: %s", err)
            return None

    async def async_get_status(self) -> dict[str, Any] | None:
        """Get the device status (from /cgi-bin/status)."""
        # C'est le point clé du Doc 2
        return await self._request("status")

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
            
        return await self._request("leds", params) is not None

    async def async_tts(self, text: str, voice: str = "claire") -> bool:
        """Send a Text-to-Speech message."""
        params = {"text": text, "voice": voice, "nocache": "1"}
        return await self._request("tts", params) is not None

    async def async_play_sound(self, url: str) -> bool:
        """Play a sound from a URL."""
        params = {"url": url}
        return await self._request("sound", params) is not None

    async def async_sound_control(self, cmd: str) -> bool:
        """Control sound playback (pause or quit)."""
        params = {"cmd": cmd}
        return await self._request("sound_control", params) is not None

    async def async_set_ears(self, left: int, right: int) -> bool:
        """Set ear positions."""
        # Note: L'API attend les positions de 0 (bas) à 16 (haut)
        params = {"left": left, "right": right, "no_memory": "1"}
        return await self._request("ears", params) is not None

    async def async_ears_random(self) -> bool:
        """Move ears randomly."""
        return await self._request("ears_random") is not None
        
    async def async_sleep(self) -> bool:
        """Put the Karotz to sleep."""
        return await self._request("sleep") is not None
        
    async def async_wakeup(self) -> bool:
        """Wake up the Karotz."""
        return await self._request("wakeup", {"silent": "1"}) is not None

    async def async_get_snapshot(self) -> bytes | None:
        """Get a camera snapshot."""
        url = f"{self._base_url}/snapshot_view?silent=1"
        try:
            async with self._session.get(url, timeout=5) as response:
                response.raise_for_status()
                return await response.read()
        except aiohttp.ClientError as err:
            LOGGER.warning("Impossible de récupérer le snapshot de la caméra: %s", err)
            return None