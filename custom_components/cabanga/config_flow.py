"""Config flow pour Cabanga."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CabangaApiClient, CabangaApiError, CabangaAuthError
from .const import CONF_REFRESH_TOKEN, CONF_SCHOOL_ID, CONF_STUDENTS, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _parse_students(raw: str) -> list[dict]:
    """Parse 'id1:Nom1, id2:Nom2' -> [{"id": "id1", "name": "Nom1"}, ...]."""
    students = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise ValueError(f"Format invalide pour '{chunk}', attendu id:Nom")
        student_id, name = chunk.split(":", 1)
        students.append({"id": student_id.strip(), "name": name.strip()})
    if not students:
        raise ValueError("Aucun élève fourni")
    return students


class CabangaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère la configuration de l'intégration Cabanga."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                students = _parse_students(user_input[CONF_STUDENTS])
            except ValueError:
                errors[CONF_STUDENTS] = "invalid_students_format"
            else:
                session = async_get_clientsession(self.hass)
                client = CabangaApiClient(session, user_input[CONF_REFRESH_TOKEN])
                try:
                    # On valide que le refresh_token fonctionne réellement
                    await client.async_refresh_access_token()
                except CabangaAuthError:
                    errors["base"] = "invalid_refresh_token"
                except CabangaApiError:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=f"Cabanga ({user_input[CONF_SCHOOL_ID]})",
                        data={
                            CONF_REFRESH_TOKEN: client.refresh_token,
                            CONF_SCHOOL_ID: user_input[CONF_SCHOOL_ID],
                            CONF_STUDENTS: students,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_REFRESH_TOKEN): str,
                vol.Required(CONF_SCHOOL_ID): str,
                vol.Required(CONF_STUDENTS): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "students_example": "75729028:Haley, 12345678:Aaron"
            },
        )
