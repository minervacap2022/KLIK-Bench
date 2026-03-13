"""Tests for Persona model and supporting types."""

from pathlib import Path

import pytest
import yaml

from klik_bench.models.persona import (
    EntityGraph,
    OrganizationEntity,
    Persona,
    PersonEntity,
    ProjectEntity,
    SessionEntry,
    UserPreferences,
)


class TestLoadFromYaml:
    def test_load_from_yaml(self, tmp_path: Path) -> None:
        """Load a full persona from YAML and verify all nested fields."""
        persona_data = {
            "id": "persona-001",
            "name": "Jordan Lee",
            "role": "Engineering Manager",
            "organization": "Acme Corp",
            "preferences": {
                "task_management": "Linear",
                "documentation": "Notion",
                "communication": "Slack",
                "file_storage": "Dropbox",
                "calendar": "Google Calendar",
                "email": "Gmail",
                "code": "GitHub",
                "timezone": "America/New_York",
                "language": "en",
                "meeting_notes_style": "bullet_points",
                "notification_preference": "urgent_only",
            },
            "user_facts": [
                {"fact": "Prefers async communication"},
                {"fact": "Manages 8 direct reports"},
            ],
            "entity_graph": {
                "people": [
                    {
                        "name": "Alex Kim",
                        "role": "Senior Engineer",
                        "relationship": "direct report",
                        "platforms": {"slack": "@alex.kim", "github": "alexkim"},
                    },
                    {
                        "name": "Sam Rivera",
                        "role": "Designer",
                        "relationship": "cross-functional partner",
                    },
                ],
                "projects": [
                    {
                        "name": "Project Phoenix",
                        "status": "active",
                        "priority": "P1",
                        "owner": "Jordan Lee",
                        "team": ["Alex Kim", "Sam Rivera"],
                        "tools": {"repo": "acme/phoenix", "board": "PHX"},
                    },
                ],
                "organizations": [
                    {
                        "name": "Acme Corp",
                        "departments": ["Engineering", "Design", "Product"],
                    },
                ],
            },
            "session_history": [
                {
                    "session_id": "sess-100",
                    "date": "2026-03-10",
                    "summary": "Sprint planning for Phoenix",
                    "decisions": ["Move deadline to March 20"],
                    "participants": ["Alex Kim", "Sam Rivera"],
                },
            ],
        }
        yaml_path = tmp_path / "persona.yaml"
        yaml_path.write_text(yaml.dump(persona_data))

        persona = Persona.from_yaml(yaml_path)

        assert persona.id == "persona-001"
        assert persona.name == "Jordan Lee"
        assert persona.role == "Engineering Manager"
        assert persona.organization == "Acme Corp"

        # Preferences
        assert persona.preferences.task_management == "Linear"
        assert persona.preferences.documentation == "Notion"
        assert persona.preferences.communication == "Slack"
        assert persona.preferences.file_storage == "Dropbox"
        assert persona.preferences.calendar == "Google Calendar"
        assert persona.preferences.email == "Gmail"
        assert persona.preferences.code == "GitHub"
        assert persona.preferences.timezone == "America/New_York"
        assert persona.preferences.language == "en"
        assert persona.preferences.meeting_notes_style == "bullet_points"
        assert persona.preferences.notification_preference == "urgent_only"

        # User facts
        assert len(persona.user_facts) == 2
        assert persona.user_facts[0] == {"fact": "Prefers async communication"}

        # Entity graph - people
        assert len(persona.entity_graph.people) == 2
        alex = persona.entity_graph.people[0]
        assert alex.name == "Alex Kim"
        assert alex.role == "Senior Engineer"
        assert alex.relationship == "direct report"
        assert alex.platforms == {"slack": "@alex.kim", "github": "alexkim"}

        sam = persona.entity_graph.people[1]
        assert sam.platforms == {}

        # Entity graph - projects
        assert len(persona.entity_graph.projects) == 1
        project = persona.entity_graph.projects[0]
        assert project.name == "Project Phoenix"
        assert project.status == "active"
        assert project.priority == "P1"
        assert project.owner == "Jordan Lee"
        assert project.team == ["Alex Kim", "Sam Rivera"]
        assert project.tools == {"repo": "acme/phoenix", "board": "PHX"}

        # Entity graph - organizations
        assert len(persona.entity_graph.organizations) == 1
        org = persona.entity_graph.organizations[0]
        assert org.name == "Acme Corp"
        assert org.departments == ["Engineering", "Design", "Product"]

        # Session history
        assert len(persona.session_history) == 1
        session = persona.session_history[0]
        assert session.session_id == "sess-100"
        assert session.date == "2026-03-10"
        assert session.summary == "Sprint planning for Phoenix"
        assert session.decisions == ["Move deadline to March 20"]
        assert session.participants == ["Alex Kim", "Sam Rivera"]


class TestResolveEntity:
    @pytest.fixture()
    def persona(self) -> Persona:
        return Persona(
            id="p-test",
            name="Test User",
            role="Manager",
            organization="TestOrg",
            preferences=UserPreferences(
                task_management="Linear",
                documentation="Notion",
                communication="Slack",
                file_storage="Dropbox",
                calendar="Google Calendar",
                email="Gmail",
                code="GitHub",
            ),
            entity_graph=EntityGraph(
                people=[
                    PersonEntity(
                        name="Alex Kim",
                        role="Engineer",
                        relationship="direct report",
                    ),
                    PersonEntity(
                        name="Dana Chen",
                        role="PM",
                        relationship="cross-functional",
                    ),
                ],
                projects=[
                    ProjectEntity(name="Project Alpha"),
                    ProjectEntity(name="Project Beta", status="completed", priority="P3"),
                ],
            ),
        )

    def test_resolve_entity_by_name(self, persona: Persona) -> None:
        """resolve_person finds 'Alex Kim' and returns None for 'Nobody'."""
        result = persona.resolve_person("Alex Kim")
        assert result is not None
        assert result.name == "Alex Kim"
        assert result.role == "Engineer"
        assert result.relationship == "direct report"

        assert persona.resolve_person("Nobody") is None

    def test_resolve_project_by_name(self, persona: Persona) -> None:
        """resolve_project finds project and returns None for nonexistent."""
        result = persona.resolve_project("Project Alpha")
        assert result is not None
        assert result.name == "Project Alpha"
        assert result.status == "active"
        assert result.priority == "P2"

        beta = persona.resolve_project("Project Beta")
        assert beta is not None
        assert beta.status == "completed"
        assert beta.priority == "P3"

        assert persona.resolve_project("Nonexistent") is None


class TestToMemoryContext:
    def test_to_memory_context(self) -> None:
        """to_memory_context generates dict with all 4 sections, preferences values correct."""
        persona = Persona(
            id="p-mem",
            name="Memory User",
            role="Analyst",
            organization="MemOrg",
            preferences=UserPreferences(
                task_management="Jira",
                documentation="Confluence",
                communication="Teams",
                file_storage="OneDrive",
                calendar="Outlook",
                email="Outlook",
                code="Azure DevOps",
                timezone="Europe/London",
                language="en",
            ),
            user_facts=[{"fact": "Left-handed"}],
            entity_graph=EntityGraph(
                people=[
                    PersonEntity(name="Bob", role="Dev", relationship="colleague"),
                ],
            ),
            session_history=[
                SessionEntry(
                    session_id="s1",
                    date="2026-03-01",
                    summary="Kickoff meeting",
                ),
            ],
        )

        ctx = persona.to_memory_context()

        # Must have all 4 top-level keys
        assert "preferences" in ctx
        assert "user_facts" in ctx
        assert "entity_graph" in ctx
        assert "session_history" in ctx

        # Preferences values
        assert ctx["preferences"]["task_management"] == "Jira"
        assert ctx["preferences"]["documentation"] == "Confluence"
        assert ctx["preferences"]["communication"] == "Teams"
        assert ctx["preferences"]["file_storage"] == "OneDrive"
        assert ctx["preferences"]["calendar"] == "Outlook"
        assert ctx["preferences"]["email"] == "Outlook"
        assert ctx["preferences"]["code"] == "Azure DevOps"
        assert ctx["preferences"]["timezone"] == "Europe/London"
        assert ctx["preferences"]["language"] == "en"

        # User facts
        assert ctx["user_facts"] == [{"fact": "Left-handed"}]

        # Entity graph
        assert len(ctx["entity_graph"]["people"]) == 1
        assert ctx["entity_graph"]["people"][0]["name"] == "Bob"

        # Session history
        assert len(ctx["session_history"]) == 1
        assert ctx["session_history"][0]["session_id"] == "s1"
