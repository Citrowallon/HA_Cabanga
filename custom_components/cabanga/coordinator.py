"""DataUpdateCoordinator pour Cabanga."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CabangaApiClient, CabangaApiError, CabangaAuthError
from .const import (
    CONF_REFRESH_TOKEN,
    CONF_SCHOOL_ID,
    DEFAULT_SCAN_INTERVAL,
    DIARY_DAYS_AFTER,
    DIARY_DAYS_BEFORE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class CabangaCoordinator(DataUpdateCoordinator):
    """Récupère périodiquement le journal/devoirs/évaluations pour tous les enfants configurés."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: CabangaApiClient,
        school_id: str,
        students: list[dict],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.entry = entry
        self.client = client
        self.school_id = school_id
        self.students = students  # [{"id": "75729028", "name": "Haley"}, ...]

    async def _async_update_data(self) -> dict:
        today = date.today()
        date_from = today - timedelta(days=DIARY_DAYS_BEFORE)
        date_to = today + timedelta(days=DIARY_DAYS_AFTER)

        result: dict[str, dict] = {}

        try:
            for student in self.students:
                student_id = student["id"]
                diary = await self.client.async_get_diary(
                    self.school_id, student_id, date_from, date_to
                )
                evaluations = await self.client.async_get_evaluations(
                    self.school_id, student_id, today.year
                )
                result[student_id] = {
                    "name": student["name"],
                    "diary": diary,
                    "evaluations": evaluations,
                }
        except CabangaAuthError as err:
            # Le refresh_token n'est plus valide : il faut reconfigurer
            # l'intégration avec un nouveau token capturé manuellement.
            raise UpdateFailed(
                "Session Cabanga expirée, reconfigurez l'intégration avec un "
                f"nouveau refresh_token : {err}"
            ) from err
        except CabangaApiError as err:
            raise UpdateFailed(f"Erreur API Cabanga : {err}") from err

        # Le refresh_token tourne à chaque appel -> on le repersiste dans le
        # config_entry pour ne pas perdre l'accès au prochain redémarrage de HA.
        if self.client.refresh_token != self.entry.data.get(CONF_REFRESH_TOKEN):
            new_data = dict(self.entry.data)
            new_data[CONF_REFRESH_TOKEN] = self.client.refresh_token
            self.hass.config_entries.async_update_entry(self.entry, data=new_data)

        return result
