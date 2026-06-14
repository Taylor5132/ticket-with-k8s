import pytest
from unittest.mock import MagicMock, call


@pytest.fixture(autouse=True)
def reset_admission_r():
    import app.admission_worker as m

    original_r = m.r
    mock_r = MagicMock()
    m.r = mock_r

    yield mock_r

    m.r = original_r


# ── issue_token ───────────────────────────────────────────

class TestIssueToken:
    def test_sets_token_in_redis(self, reset_admission_r):
        mock_r = reset_admission_r
        from app.admission_worker import issue_token

        issue_token({"performance_id": "perf1", "show_date": "2026-01-01", "user_id": "u1"})

        mock_r.set.assert_called_once()
        args, kwargs = mock_r.set.call_args
        assert args[0] == "token:perf1:2026-01-01:u1"
        assert args[1] == "valid"
        assert "ex" in kwargs

    def test_token_ttl_is_set(self, reset_admission_r):
        mock_r = reset_admission_r
        from app.admission_worker import issue_token, ADMISSION_TOKEN_TTL

        issue_token({"performance_id": "p", "show_date": "2026-01-01", "user_id": "u"})
        _, kwargs = mock_r.set.call_args
        assert kwargs["ex"] == ADMISSION_TOKEN_TTL


# ── process_entries ───────────────────────────────────────

class TestProcessEntries:
    def test_processes_all_entries_and_acks(self, reset_admission_r):
        mock_r = reset_admission_r
        from app.admission_worker import process_entries

        entries = [
            ("msg-1", {"performance_id": "p1", "show_date": "2026-01-01", "user_id": "u1"}),
            ("msg-2", {"performance_id": "p1", "show_date": "2026-01-01", "user_id": "u2"}),
        ]
        result = process_entries(entries)
        assert result == 2
        assert mock_r.xack.call_count == 2

    def test_skips_xack_when_issue_token_fails(self, reset_admission_r):
        mock_r = reset_admission_r
        mock_r.set.side_effect = Exception("Redis 장애")
        from app.admission_worker import process_entries

        entries = [("msg-1", {"performance_id": "p", "show_date": "2026-01-01", "user_id": "u"})]
        result = process_entries(entries)
        assert result == 0
        mock_r.xack.assert_not_called()

    def test_partial_failure_continues(self, reset_admission_r):
        mock_r = reset_admission_r
        mock_r.set.side_effect = [Exception("fail"), None]
        from app.admission_worker import process_entries

        entries = [
            ("msg-1", {"performance_id": "p", "show_date": "2026-01-01", "user_id": "u1"}),
            ("msg-2", {"performance_id": "p", "show_date": "2026-01-01", "user_id": "u2"}),
        ]
        result = process_entries(entries)
        assert result == 1
        mock_r.xack.assert_called_once()

    def test_empty_entries_returns_zero(self, reset_admission_r):
        from app.admission_worker import process_entries
        assert process_entries([]) == 0


# ── reclaim_stale ─────────────────────────────────────────

class TestReclaimStale:
    def test_no_stale_entries(self, reset_admission_r):
        mock_r = reset_admission_r
        mock_r.xautoclaim.return_value = ("0-0", [], [])
        from app.admission_worker import reclaim_stale

        assert reclaim_stale() == 0

    def test_reclaims_and_issues_token(self, reset_admission_r):
        mock_r = reset_admission_r
        entry = ("msg-1", {"performance_id": "p1", "show_date": "2026-01-01", "user_id": "u1"})
        mock_r.xautoclaim.side_effect = [
            ("123-0", [entry], []),
            ("0-0", [], []),
        ]
        from app.admission_worker import reclaim_stale

        result = reclaim_stale()
        assert result == 1
        mock_r.set.assert_called_once()

    def test_multiple_stale_batches(self, reset_admission_r):
        mock_r = reset_admission_r
        e1 = ("msg-1", {"performance_id": "p", "show_date": "2026-01-01", "user_id": "u1"})
        e2 = ("msg-2", {"performance_id": "p", "show_date": "2026-01-01", "user_id": "u2"})
        mock_r.xautoclaim.side_effect = [
            ("100-0", [e1], []),
            ("200-0", [e2], []),
            ("0-0", [], []),
        ]
        from app.admission_worker import reclaim_stale

        result = reclaim_stale()
        assert result == 2
