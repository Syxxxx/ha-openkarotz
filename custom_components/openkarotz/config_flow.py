"""Config flow for OpenKarotz."""
import logging
from typing import Any
import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .const import DOMAIN, LOGGER

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): selector.TextSelector(),
        vol.Required(CONF_NAME, default="Karotz"): selector.TextSelector(),
    }
)

class OpenKarotzConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenKarotz."""

    VERSION = 1

    async def _test_connection(self, host: str) -> bool:
        """Test connection to the Karotz device using /cgi-bin/status."""
        session = async_get_clientsession(self.hass)
        url = f"http://{host}/cgi-bin/status"
        try:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    try:
                        # Vérifier si la réponse est un JSON valide (comme attendu de /status)
                        await response.json()
                        return True
                    except (aiohttp.ContentTypeError, ValueError):
                        LOGGER.error("Connexion à %s réussie, mais la réponse n'est pas un JSON valide.", host)
                        return False
                return False
        except (aiohttp.ClientError, TimeoutError):
            LOGGER.debug("Échec de la connexion à %s", host)
            return False
        except Exception as err:
            LOGGER.error("Erreur inattendue lors de la connexion à %s: %s", host, err)
            return False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            
            # Utiliser l'IP comme ID unique
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Tester la connexion
            if await self._test_connection(host):
                LOGGER.info("Connexion au Karotz à %s réussie", host)
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )
            else:
                errors["base"] = "cannot_connect"

        # Afficher le formulaire
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )