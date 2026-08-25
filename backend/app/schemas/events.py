"""Pydantic models for operational event ingestion."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ResourceType(str, Enum):
    equipment = "equipment"
    actor = "actor"
    location = "location"


class EventStatus(str, Enum):
    DOWN = "DOWN"
    UP = "UP"
    DEGRADED = "DEGRADED"


class ResourceEventIn(BaseModel):
    production_id: str = Field(..., min_length=1)
    resource_type: ResourceType
    resource_id: str = Field(..., min_length=1)
    status: EventStatus
    event_time: datetime | None = None
    notes: str = ""

    @field_validator("production_id", "resource_id")
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str) -> str:
        return value.strip() if value else ""


class EquipmentEventIn(BaseModel):
    """Plan-compatible body for POST /api/events/equipment."""

    production_id: str = Field(..., min_length=1)
    equipment_id: str = Field(..., min_length=1)
    status: EventStatus
    event_time: datetime | None = None
    notes: str = ""

    @field_validator("production_id", "equipment_id")
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    def to_resource_event(self) -> ResourceEventIn:
        return ResourceEventIn(
            production_id=self.production_id,
            resource_type=ResourceType.equipment,
            resource_id=self.equipment_id,
            status=self.status,
            event_time=self.event_time,
            notes=self.notes or "",
        )


class EventIngestResponse(BaseModel):
    event_id: UUID
    stored: bool = True
    incident_id: str | None = None
