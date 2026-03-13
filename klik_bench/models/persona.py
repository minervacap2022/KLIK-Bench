"""Persona model and supporting types for KLIK-Bench."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class UserPreferences(BaseModel):
    """User tool preferences and locale settings."""

    task_management: str
    documentation: str
    communication: str
    file_storage: str
    calendar: str
    email: str
    code: str
    timezone: str = "UTC"
    language: str = "en"
    meeting_notes_style: str | None = None
    notification_preference: str | None = None


class PersonEntity(BaseModel):
    """A person in the user's entity graph."""

    name: str
    role: str
    relationship: str
    platforms: dict[str, str] = {}


class ProjectEntity(BaseModel):
    """A project in the user's entity graph."""

    name: str
    status: str = "active"
    priority: str = "P2"
    owner: str | None = None
    team: list[str] = []
    tools: dict[str, str] = {}


class OrganizationEntity(BaseModel):
    """An organization in the user's entity graph."""

    name: str
    departments: list[str] = []


class EntityGraph(BaseModel):
    """The user's knowledge graph of people, projects, and organizations."""

    people: list[PersonEntity] = []
    projects: list[ProjectEntity] = []
    organizations: list[OrganizationEntity] = []


class SessionEntry(BaseModel):
    """A single session in the user's history."""

    session_id: str
    date: str
    summary: str
    decisions: list[str] = []
    participants: list[str] = []


class Persona(BaseModel):
    """A KLIK-Bench user persona with preferences, entity graph, and session history."""

    id: str
    name: str
    role: str
    organization: str
    preferences: UserPreferences
    user_facts: list[dict[str, Any]] = []
    entity_graph: EntityGraph = EntityGraph()
    session_history: list[SessionEntry] = []

    @classmethod
    def from_yaml(cls, path: Path) -> "Persona":
        """Load a Persona from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def resolve_person(self, name: str) -> PersonEntity | None:
        """Find a person by name in the entity graph."""
        for person in self.entity_graph.people:
            if person.name == name:
                return person
        return None

    def resolve_project(self, name: str) -> ProjectEntity | None:
        """Find a project by name in the entity graph."""
        for project in self.entity_graph.projects:
            if project.name == name:
                return project
        return None

    def to_memory_context(self) -> dict[str, Any]:
        """Export persona data as a memory context dict."""
        return {
            "preferences": self.preferences.model_dump(),
            "user_facts": self.user_facts,
            "entity_graph": self.entity_graph.model_dump(),
            "session_history": [s.model_dump() for s in self.session_history],
        }
