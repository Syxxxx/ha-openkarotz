"""DataUpdateCoordinator for OpenKarotz."""
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KarotzApiClient
from .const import DOMAIN, LOGGER, COORDINATOR_POLL_INTERVAL

class KarotzCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manages polling for Karotz status data."""

    def __init__(self, hass: HomeAssistant, client: KarotzApiClient) -> None:
        """Initialize the data update coordinator."""
        self.client = client
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=COORDINATOR_POLL_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """
        Fetch data from /cgi-bin/status.
        C'est l'implémentation de l'idée clé du Doc 2.
        """
        try:
            data = await self.client.async_get_status()
            if data:
                LOGGER.debug("Données du coordinateur mises à jour: %s", data)
                return data
            
            LOGGER.debug("Le Karotz a retourné une réponse vide depuis /status")
            raise UpdateFailed("Le Karotz a retourné une réponse vide depuis /status")

        except ConnectionError as err:
            LOGGER.error("Échec de la connexion lors de la mise à jour du coordinateur: %s", err)
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            LOGGER.error("Erreur inattendue lors de la mise à jour du coordinateur: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err