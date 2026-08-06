"""Intégration Cabanga pour Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import CabangaApiClient
from .const import CONF_REFRESH_TOKEN, CONF_SCHOOL_ID, CONF_STUDENTS, DOMAIN
from .coordinator import CabangaCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialise l'intégration à partir d'une config entry."""
    session = hass.helpers.aiohttp_client.async_get_clientsession()

    client = CabangaApiClient(session, entry.data[CONF_REFRESH_TOKEN])

    coordinator = CabangaCoordinator(
        hass,
        entry,
        client,
        entry.data[CONF_SCHOOL_ID],
        entry.data[CONF_STUDENTS],
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge une config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
