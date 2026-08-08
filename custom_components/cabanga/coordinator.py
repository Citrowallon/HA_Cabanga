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
    DEFAULT_SCAN_INTERVAL,
    DIARY_DAYS_AFTER,
    DIARY_DAYS_BEFORE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _current_school_year(today: date) -> int:
    """Retourne l'année de début de l'année scolaire en cours.

    Cabanga identifie une année scolaire par son année de début (ex. l'année
    scolaire 2025-2026 est "year=2025"). L'année scolaire démarre en
    septembre : avant septembre, on est encore dans l'année scolaire ayant
    débuté l'année civile précédente.
    """
    if today.month >= 9:
        return today.year
    return today.year - 1


class CabangaCoordinator(DataUpdateCoordinator):
    """Récupère périodiquement le journal/devoirs/évaluations pour tous les enfants configurés."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: CabangaApiClient,
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
        self.students = students  # [{"school_id": "CSJCHENEE", "id": "75729028", "name": "Haley"}, ...]

    async def _async_update_data(self) -> dict:
        today = date.today()
        date_from = today - timedelta(days=DIARY_DAYS_BEFORE)
        date_to = today + timedelta(days=DIARY_DAYS_AFTER)

        result: dict[str, dict] = {}

        try:
            for student in self.students:
                student_id = student["id"]
                school_id = student["school_id"]
                diary = await self.client.async_get_diary(
                    school_id, student_id, date_from, date_to
                )
                evaluations = await self.client.async_get_evaluations(
                    school_id, student_id, _current_school_year(today)
                )
                result[student_id] = {
                    "name": student["name"],
                    "school_id": school_id,
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
