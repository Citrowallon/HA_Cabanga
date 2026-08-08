"""Capteurs Cabanga : journal de classe, devoirs à faire, dernière évaluation."""
from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CabangaCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: CabangaCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []
    for student in coordinator.students:
        student_id = student["id"]
        entities.append(CabangaJournalSensor(coordinator, entry, student_id))
        entities.append(CabangaHomeworkSensor(coordinator, entry, student_id))
        entities.append(CabangaEvaluationSensor(coordinator, entry, student_id))

    async_add_entities(entities)


class _CabangaBaseSensor(CoordinatorEntity[CabangaCoordinator], SensorEntity):
    """Base commune : device par enfant + nom lisible."""

    def __init__(self, coordinator: CabangaCoordinator, entry: ConfigEntry, student_id: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._student_id = student_id

    @property
    def _student_data(self) -> dict:
        return self.coordinator.data.get(self._student_id, {})

    @property
    def _student_name(self) -> str:
        return self._student_data.get("name", self._student_id)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._student_id)},
            name=f"Cabanga - {self._student_name}",
            manufacturer="Scolares",
            model="Cabanga",
        )


class CabangaJournalSensor(_CabangaBaseSensor):
    """Cours/activités du jour pour l'enfant."""

    _attr_icon = "mdi:notebook-outline"

    def __init__(self, coordinator, entry, student_id) -> None:
        super().__init__(coordinator, entry, student_id)
        self._attr_unique_id = f"{DOMAIN}_{student_id}_journal"
        self._attr_name = f"Journal de classe {self._student_name_init(coordinator, student_id)}"

    @staticmethod
    def _student_name_init(coordinator, student_id) -> str:
        return coordinator.data.get(student_id, {}).get("name", student_id) if coordinator.data else student_id

    @property
    def native_value(self) -> int:
        return len(self._today_entries())

    @property
    def extra_state_attributes(self) -> dict:
        entries = self._today_entries()
        return {
            "cours": [
                {
                    "heure": e.get("hour"),
                    "matiere": e.get("lessonName"),
                    "sujet": e.get("lessonSubject"),
                }
                for e in sorted(entries, key=lambda e: e.get("hour") or "")
            ]
        }

    def _today_entries(self) -> list[dict]:
        today_str = date.today().isoformat()
        diary = self._student_data.get("diary", [])
        return [e for e in diary if e.get("date") == today_str]


class CabangaHomeworkSensor(_CabangaBaseSensor):
    """Nombre de devoirs non faits à venir."""

    _attr_icon = "mdi:notebook-check-outline"

    def __init__(self, coordinator, entry, student_id) -> None:
        super().__init__(coordinator, entry, student_id)
        self._attr_unique_id = f"{DOMAIN}_{student_id}_devoirs"
        name = self._student_name_init(coordinator, student_id)
        self._attr_name = f"Devoirs à faire {name}"

    @staticmethod
    def _student_name_init(coordinator, student_id) -> str:
        return coordinator.data.get(student_id, {}).get("name", student_id) if coordinator.data else student_id

    @property
    def native_value(self) -> int:
        return len(self._pending_homework())

    @property
    def extra_state_attributes(self) -> dict:
        pending = sorted(self._pending_homework(), key=lambda e: e.get("date") or "")
        return {
            "devoirs": [
                {
                    "date": e.get("date"),
                    "matiere": e.get("lessonName"),
                    "consigne": e.get("homework"),
                }
                for e in pending
            ]
        }

    def _pending_homework(self) -> list[dict]:
        diary = self._student_data.get("diary", [])
        return [
            e for e in diary if e.get("homework") and e.get("homeworkDone") is False
        ]


class CabangaEvaluationSensor(_CabangaBaseSensor):
    """Dernière évaluation (note) reçue."""

    _attr_icon = "mdi:school-outline"

    def __init__(self, coordinator, entry, student_id) -> None:
        super().__init__(coordinator, entry, student_id)
        self._attr_unique_id = f"{DOMAIN}_{student_id}_derniere_evaluation"
        name = self._student_name_init(coordinator, student_id)
        self._attr_name = f"Dernière évaluation {name}"

    @staticmethod
    def _student_name_init(coordinator, student_id) -> str:
        return coordinator.data.get(student_id, {}).get("name", student_id) if coordinator.data else student_id

    @property
    def _sorted_evaluations(self) -> list[dict]:
        evaluations = self._student_data.get("evaluations", [])
        # Ignore les évaluations "formatives" (non cotées) pour le tri par défaut
        return sorted(
            evaluations, key=lambda e: e.get("date") or "", reverse=True
        )

    @property
    def native_value(self) -> float | None:
        evals = self._sorted_evaluations
        if not evals:
            return None
        latest = evals[0]
        score = latest.get("score")
        try:
            return float(score)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict:
        evals = self._sorted_evaluations
        if not evals:
            return {}
        latest = evals[0]
        return {
            "matiere": latest.get("subject"),
            "titre": latest.get("title"),
            "date": latest.get("date"),
            "score_max": latest.get("maximumScore"),
            "formative": latest.get("formative"),
            "5_dernieres": [
                {
                    "date": e.get("date"),
                    "matiere": e.get("subject"),
                    "titre": e.get("title"),
                    "score": e.get("score"),
                    "score_max": e.get("maximumScore"),
                }
                for e in evals[:5]
            ],
            "toutes": [
                {
                    "date": e.get("date"),
                    "matiere": e.get("subject"),
                    "titre": e.get("title"),
                    "score": e.get("score"),
                    "score_max": e.get("maximumScore"),
                    "formative": e.get("formative"),
                }
                for e in evals
            ],
        }
