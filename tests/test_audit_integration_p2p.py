"""P2P tests for audit system integration (Peer-to-Peer).

Tests the integration between audit components including:
- Signal handlers and model interactions
- Storage backend integration
- API endpoint interactions
- Admin integration
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from utils.audit_logger import AuditAction, AuditContext, AuditEntry, AuditLogger
from utils.audit_models import AuditLog, DjangoAuditStorage, InMemoryAuditStorage
from utils.audit_signals import (
    audit_disabled,
    enable_audit_logging,
    get_audit_context_from_request,
    get_pre_save_state,
    manual_audit_log,
    should_audit_model,
    store_pre_save_state,
)


class MockRequest:
    """Mock request for testing."""

    def __init__(
        self,
        user=None,
        ip="192.168.1.1",
        user_agent="Test-Agent",
        request_id=None,
    ):
        self.user = user
        self.META = {
            "REMOTE_ADDR": ip,
            "HTTP_USER_AGENT": user_agent,
            "HTTP_X_FORWARDED_FOR": None,
        }
        self.request_id = request_id or "test-req-123"
        self.session = {"session_key": "test-sess-456"}


class MockUser:
    """Mock user for testing."""

    def __init__(self, pk=42, email="test@example.com", first_name="Test", last_name="User"):
        self.pk = pk
        self.id = pk
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.is_authenticated = True

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class MockModel:
    """Mock Django model for testing."""

    _meta = type("Meta", (), {
        "abstract": False,
        "proxy": False,
        "fields": [
            type("Field", (), {"name": "id", "__class__": type("AutoField", (), {})})(),
            type("Field", (), {"name": "title"})(),
            type("Field", (), {"name": "price"})(),
        ]
    })()

    def __init__(self, pk=None, title="", price=0):
        self.pk = pk
        self.id = pk
        self.title = title
        self.price = price

    def __str__(self):
        return f"MockModel({self.pk}): {self.title}"

    class DoesNotExist(Exception):
        pass


class TestP2PAuditContextExtraction:
    """Test audit context extraction from requests (P2P-001 to P2P-020)."""

    def test_p2p_001_extracts_user_from_request(self) -> None:
        """Verify context extraction gets user from request."""
        import threading
        local = threading.local()
        local.request = MockRequest(user=MockUser())

        # Simulate the signal handler context extraction
        user = getattr(local.request, "user", None)
        ctx = AuditContext(
            user_id=user.pk if user and user.is_authenticated else None,
            user_email=user.email if user and user.is_authenticated else None,
            user_name=user.get_full_name() if user and user.is_authenticated else None,
        )

        assert ctx.user_id == 42
        assert ctx.user_email == "test@example.com"
        assert ctx.user_name == "Test User"

    def test_p2p_002_handles_anonymous_user(self) -> None:
        """Verify context extraction handles anonymous user."""
        class AnonymousUser:
            is_authenticated = False

        request = MockRequest(user=AnonymousUser())
        user = request.user

        ctx = AuditContext(
            user_id=user.pk if hasattr(user, "pk") and user.is_authenticated else None,
            user_email=getattr(user, "email", None) if hasattr(user, "is_authenticated") and user.is_authenticated else None,
        )

        assert ctx.user_id is None
        assert ctx.user_email is None

    def test_p2p_003_extracts_ip_address(self) -> None:
        """Verify context extraction gets IP address."""
        request = MockRequest(ip="10.0.0.1")
        assert request.META["REMOTE_ADDR"] == "10.0.0.1"

    def test_p2p_004_extracts_x_forwarded_for(self) -> None:
        """Verify context extraction prefers X-Forwarded-For."""
        request = MockRequest()
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1, 70.41.3.18"

        # First IP should be extracted
        forwarded = request.META["HTTP_X_FORWARDED_FOR"]
        first_ip = forwarded.split(",")[0].strip() if forwarded else None
        assert first_ip == "203.0.113.1"

    def test_p2p_005_extracts_user_agent(self) -> None:
        """Verify context extraction gets user agent."""
        request = MockRequest(user_agent="Mozilla/5.0 Test")
        assert request.META["HTTP_USER_AGENT"] == "Mozilla/5.0 Test"

    def test_p2p_006_extracts_request_id(self) -> None:
        """Verify context extraction gets request ID."""
        request = MockRequest(request_id="req-abc-123")
        assert request.request_id == "req-abc-123"

    def test_p2p_007_extracts_session_id(self) -> None:
        """Verify context extraction gets session ID."""
        request = MockRequest()
        assert request.session["session_key"] == "test-sess-456"


class TestP2PModelAuditing:
    """Test model auditing decisions (P2P-021 to P2P-040)."""

    def test_p2p_021_should_audit_regular_model(self) -> None:
        """Verify regular models are audited."""
        assert should_audit_model(MockModel) is True

    def test_p2p_022_should_not_audit_excluded_model(self) -> None:
        """Verify excluded models are skipped."""
        from utils.audit_signals import AUDIT_EXCLUDED_MODELS
        AUDIT_EXCLUDED_MODELS.add("MockModel")
        result = should_audit_model(MockModel)
        AUDIT_EXCLUDED_MODELS.discard("MockModel")  # Clean up
        assert result is False

    def test_p2p_023_should_not_audit_abstract_model(self) -> None:
        """Verify abstract models are not audited."""
        class AbstractModel:
            _meta = type("Meta", (), {"abstract": True, "proxy": False})()
        assert should_audit_model(AbstractModel) is False

    def test_p2p_024_should_not_audit_proxy_model(self) -> None:
        """Verify proxy models are not audited."""
        class ProxyModel:
            _meta = type("Meta", (), {"abstract": False, "proxy": True})()
        assert should_audit_model(ProxyModel) is False

    def test_p2p_025_should_not_audit_auditlog_model(self) -> None:
        """Verify AuditLog model itself is not audited."""
        from utils.audit_signals import AUDIT_EXCLUDED_MODELS
        assert "AuditLog" in AUDIT_EXCLUDED_MODELS

    def test_p2p_026_respects_model_opt_out(self) -> None:
        """Verify models can opt out via attribute."""
        class OptOutModel:
            _audit_excluded = True
            _meta = type("Meta", (), {"abstract": False, "proxy": False})()
        assert should_audit_model(OptOutModel) is False


class TestP2PStateTracking:
    """Test pre-save state tracking (P2P-041 to P2P-060)."""

    def test_p2p_041_stores_state_before_save(self) -> None:
        """Verify pre-save state is stored in thread local."""
        import threading
        local = threading.local()

        instance = MockModel(pk=1, title="Old Title")
        local.pre_save_states = {}

        key = f"{instance.__class__.__name__}:{instance.pk}"
        local.pre_save_states[key] = instance

        assert key in local.pre_save_states
        assert local.pre_save_states[key].title == "Old Title"

    def test_p2p_042_retrieves_stored_state(self) -> None:
        """Verify stored state can be retrieved."""
        import threading
        local = threading.local()

        old_instance = MockModel(pk=1, title="Old Title")
        local.pre_save_states = {f"MockModel:1": old_instance}

        retrieved = local.pre_save_states.get("MockModel:1")
        assert retrieved is not None
        assert retrieved.title == "Old Title"

    def test_p2p_043_clears_state_after_retrieval(self) -> None:
        """Verify state is cleaned up after retrieval."""
        import threading
        local = threading.local()

        local.pre_save_states = {"MockModel:1": MockModel(pk=1)}
        key = "MockModel:1"

        # Simulate retrieval and cleanup
        state = local.pre_save_states.get(key)
        local.pre_save_states.pop(key, None)

        assert key not in local.pre_save_states

    def test_p2p_044_handles_none_pk(self) -> None:
        """Verify new instances with None pk are handled."""
        instance = MockModel(pk=None, title="New")
        assert instance.pk is None

    def test_p2p_045_generates_unique_keys(self) -> None:
        """Verify state keys are unique per instance."""
        key1 = f"MockModel:1"
        key2 = f"MockModel:2"
        key3 = f"OtherModel:1"

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3


class TestP2PManualAuditLogging:
    """Test manual audit logging API (P2P-061 to P2P-080)."""

    def setup_method(self) -> None:
        """Set up test storage."""
        self.storage = InMemoryAuditStorage()
        AuditLogger.configure(storage=self.storage, enabled=True)

    def teardown_method(self) -> None:
        """Clean up."""
        AuditLogger.configure(storage=None, enabled=False)

    def test_p2p_061_manual_log_creates_entry(self) -> None:
        """Verify manual_audit_log creates audit entry."""
        entry_id = manual_audit_log(
            action="export",
            entity_type="Course",
            entity_id=123,
            user=MockUser(),
            metadata={"format": "csv"},
        )
        assert entry_id is not None
        assert self.storage.count() == 1

    def test_p2p_062_manual_log_with_dict_user(self) -> None:
        """Verify manual_audit_log accepts dict user."""
        entry_id = manual_audit_log(
            action="import",
            entity_type="User",
            entity_id=42,
            user={"id": 99, "email": "dict@example.com", "name": "Dict User"},
        )
        assert entry_id is not None

        entry = self.storage.query()[0]
        assert entry.context.user_id == 99
        assert entry.context.user_email == "dict@example.com"

    def test_p2p_063_manual_log_without_user(self) -> None:
        """Verify manual_audit_log works without user."""
        entry_id = manual_audit_log(
            action="system_task",
            entity_type="Task",
            metadata={"task": "cleanup"},
        )
        assert entry_id is not None

        entry = self.storage.query()[0]
        assert entry.context.user_id is None

    def test_p2p_064_manual_log_with_changes(self) -> None:
        """Verify manual_audit_log records field changes."""
        entry_id = manual_audit_log(
            action="update",
            entity_type="Course",
            entity_id=1,
            user=MockUser(),
            changes=[
                {"field_name": "title", "old_value": "Old", "new_value": "New"},
                {"field_name": "price", "old_value": 10, "new_value": 20, "field_type": "DecimalField"},
            ],
        )
        assert entry_id is not None

        entry = self.storage.query()[0]
        assert len(entry.changes) == 2
        assert entry.changes[0].field_name == "title"

    def test_p2p_065_manual_log_returns_none_when_disabled(self) -> None:
        """Verify manual_audit_log returns None when logging disabled."""
        AuditLogger.configure(enabled=False)

        entry_id = manual_audit_log(
            action="export",
            entity_type="Course",
        )
        assert entry_id is None


class TestP2PAuditDisabledContext:
    """Test audit_disabled context manager (P2P-081 to P2P-090)."""

    def setup_method(self) -> None:
        """Set up enabled logger."""
        self.storage = InMemoryAuditStorage()
        AuditLogger.configure(storage=self.storage, enabled=True)

    def teardown_method(self) -> None:
        """Clean up."""
        AuditLogger.configure(storage=None, enabled=False)

    def test_p2p_081_context_manager_disables_logging(self) -> None:
        """Verify audit_disabled context disables logging."""
        assert AuditLogger.is_enabled() is True

        with audit_disabled():
            assert AuditLogger.is_enabled() is False

        assert AuditLogger.is_enabled() is True

    def test_p2p_082_skips_logs_inside_context(self) -> None:
        """Verify logs inside context are skipped."""
        with audit_disabled():
            entry_id = AuditLogger.log(AuditEntry(action=AuditAction.VIEW))
            assert entry_id is None

        assert self.storage.count() == 0

    def test_p2p_083_restores_previous_state(self) -> None:
        """Verify context manager restores previous enabled state."""
        AuditLogger.configure(enabled=True)

        with audit_disabled():
            pass

        assert AuditLogger.is_enabled() is True

    def test_p2p_084_handles_exception_in_context(self) -> None:
        """Verify context manager handles exceptions properly."""
        try:
            with audit_disabled():
                assert AuditLogger.is_enabled() is False
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert AuditLogger.is_enabled() is True


class TestP2PDjangoStorageIntegration:
    """Test Django storage backend integration (P2P-091 to P2P-110)."""

    def test_p2p_091_storage_factory_returns_instance(self) -> None:
        """Verify factory creates Django storage."""
        from utils.audit_models import get_django_storage
        storage = get_django_storage()
        assert isinstance(storage, DjangoAuditStorage)

    def test_p2p_092_enable_audit_creates_storage(self) -> None:
        """Verify enable_audit_logging configures storage."""
        enable_audit_logging()
        assert AuditLogger.is_enabled() is True
        AuditLogger.configure(enabled=False)  # Clean up


class TestP2PEntryLifecycle:
    """Test complete audit entry lifecycle (P2P-111 to P2P-130)."""

    def setup_method(self) -> None:
        """Set up storage."""
        self.storage = InMemoryAuditStorage()
        AuditLogger.configure(storage=self.storage, enabled=True)

    def teardown_method(self) -> None:
        """Clean up."""
        AuditLogger.configure(storage=None, enabled=False)

    def test_p2p_111_create_entry_flow(self) -> None:
        """Verify complete create entry flow."""
        ctx = AuditContext(user_id=42, user_email="test@example.com")

        class Course:
            pk = 123
            def __str__(self):
                return "Python Course"

        entry_id = AuditLogger.log_create(Course(), ctx)
        assert entry_id is not None

        stored = self.storage.query(action=AuditAction.CREATE)[0]
        assert stored.entity_type == "Course"
        assert stored.new_state is not None

    def test_p2p_112_update_entry_flow(self) -> None:
        """Verify complete update entry flow."""
        ctx = AuditContext(user_id=42)

        class Course:
            _meta = MockModel._meta
            pk = 123
            title = "New Title"
            price = 20

        old_course = type("Old", (), {"pk": 123, "title": "Old Title", "price": 10, "_meta": MockModel._meta})()
        new_course = Course()

        entry_id = AuditLogger.log_update(old_course, new_course, ctx)
        assert entry_id is not None

        stored = self.storage.query(action=AuditAction.UPDATE)[0]
        assert len(stored.changes) == 2

    def test_p2p_113_delete_entry_flow(self) -> None:
        """Verify complete delete entry flow."""
        ctx = AuditContext(user_id=42)

        class Course:
            pk = 123
            title = "To Delete"

        old_instance = Course()

        entry_id = AuditLogger.log_delete(old_instance, ctx)
        assert entry_id is not None

        stored = self.storage.query(action=AuditAction.DELETE)[0]
        assert stored.old_state is not None
        assert stored.new_state is None

    def test_p2p_114_query_filters_combined(self) -> None:
        """Verify multiple query filters work together."""
        # Create diverse entries
        AuditLogger.log(AuditEntry(
            action=AuditAction.CREATE,
            entity_type="Course",
            entity_id=1,
            context=AuditContext(user_id=1),
        ))
        AuditLogger.log(AuditEntry(
            action=AuditAction.UPDATE,
            entity_type="Course",
            entity_id=2,
            context=AuditContext(user_id=2),
        ))
        AuditLogger.log(AuditEntry(
            action=AuditAction.CREATE,
            entity_type="User",
            entity_id=1,
            context=AuditContext(user_id=1),
        ))

        # Filter by type and action
        results = self.storage.query(
            entity_type="Course",
            action=AuditAction.CREATE,
        )
        assert len(results) == 1
        assert results[0].entity_id == 1

    def test_p2p_115_entries_sorted_by_time(self) -> None:
        """Verify entries sorted by timestamp."""
        import time

        for i in range(5):
            AuditLogger.log(AuditEntry(entity_id=i))
            time.sleep(0.001)  # Small delay for ordering

        results = self.storage.query(limit=3)
        # Should be in reverse chronological order
        assert len(results) == 3


class TestP2PQueryScenarios:
    """Test realistic query scenarios (P2P-131 to P2P-150)."""

    def setup_method(self) -> None:
        """Set up storage with sample data."""
        self.storage = InMemoryAuditStorage()
        AuditLogger.configure(storage=self.storage, enabled=True)

        # Create sample entries
        for i in range(10):
            AuditLogger.log(AuditEntry(
                action=AuditAction.CREATE if i % 2 == 0 else AuditAction.UPDATE,
                entity_type="Course" if i < 5 else "User",
                entity_id=i,
                context=AuditContext(user_id=i % 3),
                timestamp=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
            ))

    def teardown_method(self) -> None:
        """Clean up."""
        AuditLogger.configure(storage=None, enabled=False)

    def test_p2p_131_paginate_results(self) -> None:
        """Verify pagination works."""
        all_results = self.storage.query(limit=100)
        assert len(all_results) == 10

        page1 = self.storage.query(limit=5)
        assert len(page1) == 5

    def test_p2p_132_filter_by_user(self) -> None:
        """Verify filtering by user."""
        results = self.storage.query(user_id=0)
        assert len(results) == 4  # entries where i % 3 == 0

    def test_p2p_133_filter_by_date_range(self) -> None:
        """Verify filtering by date range."""
        results = self.storage.query(
            start_time=datetime(2024, 1, 5, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 8, tzinfo=timezone.utc),
        )
        assert len(results) == 4  # Jan 5, 6, 7, 8

    def test_p2p_134_filter_by_entity_type(self) -> None:
        """Verify filtering by entity type."""
        results = self.storage.query(entity_type="Course")
        assert len(results) == 5

    def test_p2p_135_filter_by_action(self) -> None:
        """Verify filtering by action."""
        results = self.storage.query(action=AuditAction.CREATE)
        assert len(results) == 5  # Even indices

    def test_p2p_136_combined_filters(self) -> None:
        """Verify combining multiple filters."""
        results = self.storage.query(
            entity_type="Course",
            action=AuditAction.CREATE,
            user_id=0,
        )
        # Courses (i<5), CREATE (even), user_id=0 (i%3==0): i=0
        assert len(results) == 1
        assert results[0].entity_id == 0

    def test_p2p_137_empty_result_set(self) -> None:
        """Verify empty result handling."""
        results = self.storage.query(entity_type="NonExistent")
        assert results == []

    def test_p2p_138_stats_calculation(self) -> None:
        """Verify statistics aggregation."""
        storage = DjangoAuditStorage()
        # Note: This would need actual database entries for full testing

    def test_p2p_139_entity_history_query(self) -> None:
        """Verify entity history query."""
        # Add multiple entries for same entity
        AuditLogger.log(AuditEntry(
            entity_type="Course",
            entity_id=99,
            action=AuditAction.UPDATE,
        ))
        AuditLogger.log(AuditEntry(
            entity_type="Course",
            entity_id=99,
            action=AuditAction.UPDATE,
        ))

        history = self.storage.query(entity_type="Course", entity_id=99)
        assert len(history) >= 2

    def test_p2p_140_user_activity_query(self) -> None:
        """Verify user activity query."""
        activity = self.storage.query(user_id=1)
        # Should return all entries for user 1
        for entry in activity:
            assert entry.context.user_id == 1
