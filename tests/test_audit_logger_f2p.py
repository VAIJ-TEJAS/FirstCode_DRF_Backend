"""Test suite for audit logger (F2P - Function to Python).

Tests the core audit logging functionality including:
- AuditEntry creation and serialization
- AuditContext building
- FieldChange detection
- AuditLogger operations
- InMemoryAuditStorage
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from utils.audit_logger import (
    AuditAction,
    AuditContext,
    AuditEntry,
    AuditLevel,
    AuditLogger,
    FieldChange,
    InMemoryAuditStorage,
)


class TestF2PAuditContext:
    """Test audit context building and serialization (F2P-001 to F2P-010)."""

    def test_f2p_001_context_stores_user_info(self) -> None:
        """Verify AuditContext stores user identification correctly."""
        ctx = AuditContext(
            user_id=42,
            user_email="test@example.com",
            user_name="Test User",
        )
        assert ctx.user_id == 42
        assert ctx.user_email == "test@example.com"
        assert ctx.user_name == "Test User"

    def test_f2p_002_context_stores_request_info(self) -> None:
        """Verify AuditContext stores request metadata correctly."""
        ctx = AuditContext(
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 Test",
            request_id="req-123",
            session_id="sess-456",
            correlation_id="corr-789",
        )
        assert ctx.ip_address == "192.168.1.1"
        assert ctx.user_agent == "Mozilla/5.0 Test"
        assert ctx.request_id == "req-123"
        assert ctx.session_id == "sess-456"
        assert ctx.correlation_id == "corr-789"

    def test_f2p_003_context_defaults_to_none(self) -> None:
        """Verify AuditContext defaults all fields to None."""
        ctx = AuditContext()
        assert ctx.user_id is None
        assert ctx.user_email is None
        assert ctx.user_name is None
        assert ctx.ip_address is None
        assert ctx.user_agent is None
        assert ctx.request_id is None
        assert ctx.session_id is None
        assert ctx.correlation_id is None

    def test_f2p_004_context_serializes_to_dict(self) -> None:
        """Verify AuditContext serializes to dictionary correctly."""
        ctx = AuditContext(
            user_id=42,
            user_email="test@example.com",
            ip_address="192.168.1.1",
        )
        data = ctx.to_dict()
        assert data["user_id"] == 42
        assert data["user_email"] == "test@example.com"
        assert data["ip_address"] == "192.168.1.1"
        assert data["user_name"] is None


class TestF2PFieldChange:
    """Test field change detection and serialization (F2P-011 to F2P-020)."""

    def test_f2p_011_field_change_stores_values(self) -> None:
        """Verify FieldChange stores field name and values."""
        change = FieldChange(
            field_name="title",
            old_value="Old Title",
            new_value="New Title",
            field_type="CharField",
        )
        assert change.field_name == "title"
        assert change.old_value == "Old Title"
        assert change.new_value == "New Title"
        assert change.field_type == "CharField"

    def test_f2p_012_field_change_serializes_to_dict(self) -> None:
        """Verify FieldChange serializes to dictionary correctly."""
        change = FieldChange(
            field_name="price",
            old_value=10.00,
            new_value=15.00,
            field_type="DecimalField",
        )
        data = change.to_dict()
        assert data["field_name"] == "price"
        assert data["old_value"] == 10.00
        assert data["new_value"] == 15.00
        assert data["field_type"] == "DecimalField"

    def test_f2p_013_field_change_handles_datetime(self) -> None:
        """Verify FieldChange properly serializes datetime values."""
        old_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        new_time = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        change = FieldChange(
            field_name="updated_at",
            old_value=old_time,
            new_value=new_time,
        )
        data = change.to_dict()
        assert "2024-01-01T12:00:00" in str(data["old_value"])
        assert "2024-01-02T12:00:00" in str(data["new_value"])

    def test_f2p_014_field_change_handles_none(self) -> None:
        """Verify FieldChange properly handles None values."""
        change = FieldChange(
            field_name="description",
            old_value=None,
            new_value="New description",
        )
        data = change.to_dict()
        assert data["old_value"] is None
        assert data["new_value"] == "New description"


class TestF2PAuditEntry:
    """Test audit entry creation and serialization (F2P-021 to F2P-040)."""

    def test_f2p_021_entry_generates_uuid(self) -> None:
        """Verify AuditEntry auto-generates UUID ID."""
        entry = AuditEntry()
        assert entry.id is not None
        assert len(entry.id) == 36  # UUID string length

    def test_f2p_022_entry_stores_timestamp(self) -> None:
        """Verify AuditEntry stores timestamp automatically."""
        before = datetime.now(timezone.utc)
        entry = AuditEntry()
        after = datetime.now(timezone.utc)
        assert before <= entry.timestamp <= after

    def test_f2p_023_entry_defaults_to_view_action(self) -> None:
        """Verify AuditEntry defaults to VIEW action."""
        entry = AuditEntry()
        assert entry.action == AuditAction.VIEW

    def test_f2p_024_entry_defaults_to_info_level(self) -> None:
        """Verify AuditEntry defaults to INFO level."""
        entry = AuditEntry()
        assert entry.level == AuditLevel.INFO

    def test_f2p_025_entry_stores_entity_info(self) -> None:
        """Verify AuditEntry stores entity identification."""
        entry = AuditEntry(
            entity_type="Course",
            entity_id=123,
            entity_repr="Python Basics",
        )
        assert entry.entity_type == "Course"
        assert entry.entity_id == 123
        assert entry.entity_repr == "Python Basics"

    def test_f2p_026_entry_stores_changes_list(self) -> None:
        """Verify AuditEntry stores list of field changes."""
        changes = [
            FieldChange("title", "Old", "New"),
            FieldChange("price", 10, 20),
        ]
        entry = AuditEntry(changes=changes)
        assert len(entry.changes) == 2
        assert entry.changes[0].field_name == "title"

    def test_f2p_027_entry_stores_state_data(self) -> None:
        """Verify AuditEntry stores old and new state."""
        old_state = {"id": 1, "title": "Old"}
        new_state = {"id": 1, "title": "New"}
        entry = AuditEntry(
            old_state=old_state,
            new_state=new_state,
        )
        assert entry.old_state == old_state
        assert entry.new_state == new_state

    def test_f2p_028_entry_stores_metadata(self) -> None:
        """Verify AuditEntry stores custom metadata."""
        entry = AuditEntry(
            metadata={"source": "api", "version": "2.0"},
        )
        assert entry.metadata["source"] == "api"
        assert entry.metadata["version"] == "2.0"

    def test_f2p_029_entry_stores_duration(self) -> None:
        """Verify AuditEntry stores operation duration."""
        entry = AuditEntry(duration_ms=150.5)
        assert entry.duration_ms == 150.5

    def test_f2p_030_entry_serializes_to_dict(self) -> None:
        """Verify AuditEntry serializes to complete dictionary."""
        entry = AuditEntry(
            action=AuditAction.UPDATE,
            entity_type="Course",
            entity_id=123,
            changes=[FieldChange("title", "Old", "New")],
        )
        data = entry.to_dict()
        assert data["action"] == "update"
        assert data["entity_type"] == "Course"
        assert data["entity_id"] == 123
        assert len(data["changes"]) == 1

    def test_f2p_031_entry_serializes_to_json(self) -> None:
        """Verify AuditEntry serializes to JSON string."""
        entry = AuditEntry(
            action=AuditAction.CREATE,
            entity_type="User",
            entity_id=42,
        )
        json_str = entry.to_json()
        data = json.loads(json_str)
        assert data["action"] == "create"
        assert data["entity_type"] == "User"

    def test_f2p_032_entry_detects_significant_changes_for_update(self) -> None:
        """Verify has_significant_changes works for updates."""
        entry = AuditEntry(
            action=AuditAction.UPDATE,
            changes=[FieldChange("title", "Old", "New")],
        )
        assert entry.has_significant_changes() is True

    def test_f2p_033_entry_detects_no_changes(self) -> None:
        """Verify has_significant_changes returns False for no-op updates."""
        entry = AuditEntry(
            action=AuditAction.UPDATE,
            changes=[FieldChange("updated_at", "old", "new")],
        )
        assert entry.has_significant_changes() is False

    def test_f2p_034_entry_always_significant_for_create(self) -> None:
        """Verify has_significant_changes returns True for create."""
        entry = AuditEntry(action=AuditAction.CREATE, changes=[])
        assert entry.has_significant_changes() is True

    def test_f2p_035_entry_always_significant_for_delete(self) -> None:
        """Verify has_significant_changes returns True for delete."""
        entry = AuditEntry(action=AuditAction.DELETE, changes=[])
        assert entry.has_significant_changes() is True


class TestF2PAuditLogger:
    """Test AuditLogger operations (F2P-041 to F2P-060)."""

    def setup_method(self) -> None:
        """Set up test storage before each test."""
        self.storage = InMemoryAuditStorage()
        AuditLogger.configure(storage=self.storage, enabled=True)

    def teardown_method(self) -> None:
        """Clean up after each test."""
        AuditLogger.configure(storage=None, enabled=False)

    def test_f2p_041_logger_enabled_with_storage(self) -> None:
        """Verify logger is enabled when storage is configured."""
        assert AuditLogger.is_enabled() is True

    def test_f2p_042_logger_disabled_without_storage(self) -> None:
        """Verify logger is disabled without storage."""
        AuditLogger.configure(storage=None)
        assert AuditLogger.is_enabled() is False

    def test_f2p_043_logger_disabled_when_configured(self) -> None:
        """Verify logger can be explicitly disabled."""
        AuditLogger.configure(enabled=False)
        assert AuditLogger.is_enabled() is False

    def test_f2p_044_logger_logs_entry(self) -> None:
        """Verify logger stores entry to storage."""
        entry = AuditEntry(
            action=AuditAction.VIEW,
            entity_type="Course",
        )
        entry_id = AuditLogger.log(entry)
        assert entry_id is not None
        assert self.storage.count() == 1

    def test_f2p_045_logger_skips_no_change_updates(self) -> None:
        """Verify logger skips updates with no significant changes."""
        entry = AuditEntry(
            action=AuditAction.UPDATE,
            entity_type="Course",
            changes=[FieldChange("updated_at", "old", "new")],
        )
        entry_id = AuditLogger.log(entry)
        assert entry_id is None
        assert self.storage.count() == 0

    def test_f2p_046_logger_logs_create(self) -> None:
        """Verify log_create creates entry for new instance."""
        # Create a mock model instance
        class MockModel:
            pk = 123
            def __str__(self):
                return "Test Course"

        instance = MockModel()
        ctx = AuditContext(user_id=42, user_email="test@example.com")

        entry_id = AuditLogger.log_create(instance, ctx)
        assert entry_id is not None

        stored = self.storage.query()[0]
        assert stored.action == AuditAction.CREATE
        assert stored.entity_type == "MockModel"
        assert stored.entity_id == 123

    def test_f2p_047_logger_logs_update(self) -> None:
        """Verify log_update creates entry for changes."""
        class MockModel:
            _meta = type("Meta", (), {
                "fields": [
                    type("Field", (), {"name": "title"})(),
                    type("Field", (), {"name": "price"})(),
                ]
            })()
            pk = 123
            title = "New Title"
            price = 20

        old = type("Old", (), {"pk": 123, "title": "Old Title", "price": 10})()
        old._meta = MockModel._meta
        new = MockModel()

        ctx = AuditContext(user_id=42)

        entry_id = AuditLogger.log_update(old, new, ctx)
        assert entry_id is not None

        stored = self.storage.query()[0]
        assert stored.action == AuditAction.UPDATE
        assert len(stored.changes) == 2

    def test_f2p_048_logger_logs_delete(self) -> None:
        """Verify log_delete creates entry for deletion."""
        class MockModel:
            pk = 123
            def __str__(self):
                return "Deleted Course"

        instance = MockModel()
        ctx = AuditContext(user_id=42)

        entry_id = AuditLogger.log_delete(instance, ctx)
        assert entry_id is not None

        stored = self.storage.query()[0]
        assert stored.action == AuditAction.DELETE
        assert stored.old_state is not None

    def test_f2p_049_logger_logs_action(self) -> None:
        """Verify log_action creates generic action entry."""
        entry_id = AuditLogger.log_action(
            action=AuditAction.EXPORT,
            entity_type="Course",
            entity_id=123,
            context=AuditContext(user_id=42),
            metadata={"format": "csv"},
        )
        assert entry_id is not None

        stored = self.storage.query()[0]
        assert stored.action == AuditAction.EXPORT
        assert stored.metadata["format"] == "csv"

    def test_f2p_050_logger_respects_ignored_models(self) -> None:
        """Verify logger respects model ignore list."""
        AuditLogger.configure(
            storage=self.storage,
            enabled=True,
            ignored_models=["IgnoredModel"],
        )
        assert AuditLogger.is_model_ignored("IgnoredModel") is True
        assert AuditLogger.is_model_ignored("OtherModel") is False


class TestF2PInMemoryStorage:
    """Test InMemoryAuditStorage implementation (F2P-061 to F2P-080)."""

    def setup_method(self) -> None:
        """Set up fresh storage."""
        self.storage = InMemoryAuditStorage()

    def test_f2p_061_storage_stores_entry(self) -> None:
        """Verify storage stores entry and returns ID."""
        entry = AuditEntry(action=AuditAction.VIEW, entity_type="Course")
        entry_id = self.storage.store(entry)
        assert entry_id == entry.id
        assert self.storage.count() == 1

    def test_f2p_062_storage_queries_by_entity_type(self) -> None:
        """Verify query filtering by entity type."""
        self.storage.store(AuditEntry(entity_type="Course"))
        self.storage.store(AuditEntry(entity_type="User"))
        self.storage.store(AuditEntry(entity_type="Course"))

        results = self.storage.query(entity_type="Course")
        assert len(results) == 2

    def test_f2p_063_storage_queries_by_entity_id(self) -> None:
        """Verify query filtering by entity ID."""
        self.storage.store(AuditEntry(entity_type="Course", entity_id=1))
        self.storage.store(AuditEntry(entity_type="Course", entity_id=2))

        results = self.storage.query(entity_type="Course", entity_id=1)
        assert len(results) == 1
        assert results[0].entity_id == 1

    def test_f2p_064_storage_queries_by_action(self) -> None:
        """Verify query filtering by action."""
        self.storage.store(AuditEntry(action=AuditAction.CREATE))
        self.storage.store(AuditEntry(action=AuditAction.UPDATE))

        results = self.storage.query(action=AuditAction.CREATE)
        assert len(results) == 1
        assert results[0].action == AuditAction.CREATE

    def test_f2p_065_storage_queries_by_user_id(self) -> None:
        """Verify query filtering by user ID."""
        self.storage.store(AuditEntry(context=AuditContext(user_id=1)))
        self.storage.store(AuditEntry(context=AuditContext(user_id=2)))

        results = self.storage.query(user_id=1)
        assert len(results) == 1
        assert results[0].context.user_id == 1

    def test_f2p_066_storage_queries_by_time_range(self) -> None:
        """Verify query filtering by time range."""
        old = AuditEntry(timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc))
        new = AuditEntry(timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc))
        self.storage.store(old)
        self.storage.store(new)

        results = self.storage.query(
            start_time=datetime(2024, 3, 1, tzinfo=timezone.utc),
        )
        assert len(results) == 1
        assert results[0].timestamp == new.timestamp

    def test_f2p_067_storage_respects_limit(self) -> None:
        """Verify query respects result limit."""
        for i in range(10):
            self.storage.store(AuditEntry(entity_id=i))

        results = self.storage.query(limit=5)
        assert len(results) == 5

    def test_f2p_068_storage_orders_by_timestamp_desc(self) -> None:
        """Verify results ordered by timestamp descending."""
        old = AuditEntry(timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc))
        new = AuditEntry(timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc))
        self.storage.store(old)
        self.storage.store(new)

        results = self.storage.query()
        assert results[0].timestamp == new.timestamp
        assert results[1].timestamp == old.timestamp

    def test_f2p_069_storage_enforces_max_entries(self) -> None:
        """Verify storage enforces maximum entry limit."""
        storage = InMemoryAuditStorage(max_entries=3)
        for i in range(5):
            storage.store(AuditEntry(entity_id=i))

        assert storage.count() == 3

    def test_f2p_070_storage_clear_empties_all(self) -> None:
        """Verify clear() removes all entries."""
        self.storage.store(AuditEntry())
        self.storage.store(AuditEntry())
        assert self.storage.count() == 2

        self.storage.clear()
        assert self.storage.count() == 0


class TestF2PAuditEnums:
    """Test AuditAction and AuditLevel enums (F2P-081 to F2P-090)."""

    def test_f2p_081_all_actions_have_values(self) -> None:
        """Verify all AuditAction variants have string values."""
        for action in AuditAction:
            assert isinstance(action.value, str)
            assert len(action.value) > 0

    def test_f2p_082_action_values_are_lowercase(self) -> None:
        """Verify action values follow naming convention."""
        for action in AuditAction:
            assert action.value == action.value.lower()

    def test_f2p_083_all_levels_have_values(self) -> None:
        """Verify all AuditLevel variants have string values."""
        for level in AuditLevel:
            assert isinstance(level.value, str)
            assert len(level.value) > 0

    def test_f2p_084_standard_actions_defined(self) -> None:
        """Verify standard CRUD actions are defined."""
        assert AuditAction.CREATE.value == "create"
        assert AuditAction.UPDATE.value == "update"
        assert AuditAction.DELETE.value == "delete"
        assert AuditAction.VIEW.value == "view"

    def test_f2p_085_auth_actions_defined(self) -> None:
        """Verify authentication actions are defined."""
        assert AuditAction.LOGIN.value == "login"
        assert AuditAction.LOGOUT.value == "logout"

    def test_f2p_086_bulk_actions_defined(self) -> None:
        """Verify bulk operation actions are defined."""
        assert AuditAction.BULK_CREATE.value == "bulk_create"
        assert AuditAction.BULK_UPDATE.value == "bulk_update"
        assert AuditAction.BULK_DELETE.value == "bulk_delete"


class TestF2PAuditEntryEdgeCases:
    """Test edge cases and error handling (F2P-091 to F2P-100)."""

    def test_f2p_091_entry_handles_empty_changes(self) -> None:
        """Verify entry handles empty changes list."""
        entry = AuditEntry(changes=[])
        data = entry.to_dict()
        assert data["changes"] == []

    def test_f2p_092_entry_handles_complex_metadata(self) -> None:
        """Verify entry handles nested metadata."""
        entry = AuditEntry(metadata={
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 42,
        })
        data = entry.to_dict()
        assert data["metadata"]["nested"]["key"] == "value"
        assert data["metadata"]["list"] == [1, 2, 3]

    def test_f2p_093_entry_repr_truncation(self) -> None:
        """Verify entity_repr is stored correctly."""
        long_repr = "A" * 300
        entry = AuditEntry(entity_repr=long_repr)
        assert entry.entity_repr == long_repr

    def test_f2p_094_context_handles_empty_strings(self) -> None:
        """Verify context handles empty string values."""
        ctx = AuditContext(
            user_email="",
            user_name="",
            user_agent="",
        )
        assert ctx.user_email == ""
        assert ctx.user_name == ""
        assert ctx.user_agent == ""

    def test_f2p_095_storage_query_with_no_matches(self) -> None:
        """Verify query returns empty list when no matches."""
        storage = InMemoryAuditStorage()
        results = storage.query(entity_type="NonExistent")
        assert results == []

    def test_f2p_096_logger_returns_none_when_disabled(self) -> None:
        """Verify logger returns None when logging is disabled."""
        AuditLogger.configure(enabled=False)
        entry = AuditEntry()
        result = AuditLogger.log(entry)
        assert result is None

    def test_f2p_097_logger_returns_none_without_storage(self) -> None:
        """Verify logger returns None without storage."""
        AuditLogger.configure(storage=None)
        entry = AuditEntry()
        result = AuditLogger.log(entry)
        assert result is None

    def test_f2p_098_serialization_handles_special_chars(self) -> None:
        """Verify JSON serialization handles special characters."""
        entry = AuditEntry(
            entity_repr='Special "chars" and \\backslash',
            metadata={"key": "value with \n newline"},
        )
        json_str = entry.to_json()
        # Should not raise exception
        data = json.loads(json_str)
        assert "Special" in data["entity_repr"]

    def test_f2p_099_entry_timestamp_timezone_aware(self) -> None:
        """Verify entry timestamp is timezone aware."""
        entry = AuditEntry()
        assert entry.timestamp.tzinfo is not None

    def test_f2p_100_multiple_stores_independent(self) -> None:
        """Verify multiple storage instances are independent."""
        storage1 = InMemoryAuditStorage()
        storage2 = InMemoryAuditStorage()

        storage1.store(AuditEntry())
        assert storage1.count() == 1
        assert storage2.count() == 0
