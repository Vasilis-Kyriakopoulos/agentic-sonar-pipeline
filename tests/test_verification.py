"""
Tests for the post-fix SonarQube verification scan feature.

Covers:
  - SonarCubeClient._wait_for_ce_task / run_scan_and_wait
  - database helpers: mark_run_verified, get_latest_successful_runs, analytics
  - Coordinator.verify_fixes
  - FastAPI /pipeline/verify endpoint
"""

import os
import sys
import time
import pytest
import logging
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# 1. SonarCubeClient tests
# ============================================================================

class TestSonarCubeClientVerification:
    """Tests for _wait_for_ce_task and run_scan_and_wait."""

    def _make_client(self):
        from sonarcube_client import SonarCubeClient
        return SonarCubeClient(url="http://sonarqube:9000", token="test-token")

    @patch("sonarcube_client.requests.get")
    def test_wait_for_ce_task_completes_immediately(self, mock_get):
        """CE returns no pending tasks on first poll → completes immediately."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"tasks": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = self._make_client()
        result = client._wait_for_ce_task("my-project", timeout=10, poll_interval=1)

        assert result is True
        mock_get.assert_called_once()

    @patch("time.sleep")
    @patch("sonarcube_client.requests.get")
    def test_wait_for_ce_task_polls_then_completes(self, mock_get, mock_sleep):
        """CE has a pending task, then completes on 2nd poll."""
        pending_resp = MagicMock()
        pending_resp.json.return_value = {"tasks": [{"status": "IN_PROGRESS"}]}
        pending_resp.raise_for_status = MagicMock()

        done_resp = MagicMock()
        done_resp.json.return_value = {"tasks": []}
        done_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [pending_resp, done_resp]

        client = self._make_client()
        result = client._wait_for_ce_task("my-project", timeout=30, poll_interval=5)

        assert result is True
        assert mock_get.call_count == 2

    @patch("time.sleep")
    @patch("sonarcube_client.requests.get")
    def test_wait_for_ce_task_timeout(self, mock_get, mock_sleep):
        """CE never finishes → returns False after timeout."""
        pending_resp = MagicMock()
        pending_resp.json.return_value = {"tasks": [{"status": "PENDING"}]}
        pending_resp.raise_for_status = MagicMock()
        mock_get.return_value = pending_resp

        client = self._make_client()
        # timeout=10, poll_interval=5 → 2 polls then timeout
        result = client._wait_for_ce_task("my-project", timeout=10, poll_interval=5)

        assert result is False

    @patch.object(
        __import__("sonarcube_client", fromlist=["SonarCubeClient"]).SonarCubeClient,
        "_wait_for_ce_task",
        return_value=True,
    )
    @patch.object(
        __import__("sonarcube_client", fromlist=["SonarCubeClient"]).SonarCubeClient,
        "run_scan",
    )
    def test_run_scan_and_wait_success(self, mock_scan, mock_wait):
        """run_scan_and_wait calls run_scan then _wait_for_ce_task."""
        client = self._make_client()
        result = client.run_scan_and_wait("/repo", "my-project")

        assert result is True
        mock_scan.assert_called_once_with("/repo", "my-project")
        mock_wait.assert_called_once()


# ============================================================================
# 2. Database tests
# ============================================================================

class TestDatabaseVerification:
    """Tests for the new DB helpers and updated analytics."""

    @pytest.fixture(autouse=True)
    def setup_db(self, tmp_path):
        """Create a fresh in-memory DB for each test."""
        import database as db

        # Override engine to use in-memory SQLite
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        self.engine = create_engine("sqlite:///:memory:", echo=False)
        db.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Seed: create an issue + a successful run
        issue = db.IssueRecord(
            key="ISSUE-1", rule="python:S1234", severity="MAJOR",
            component="proj:src/main.py", file_path="src/main.py",
            line=10, message="Test issue", type="BUG",
            project_key="my-project", status="FIXED",
        )
        self.session.add(issue)
        self.session.commit()

        run = db.PipelineRun(
            issue_key="ISSUE-1", session_branch="fix/test",
            verdict="SUCCESS", attempts=1,
            started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
        )
        self.session.add(run)
        self.session.commit()
        self.run_id = run.id

        yield

        self.session.close()

    def test_mark_run_verified_true(self):
        import database as db
        db.mark_run_verified(self.session, self.run_id, True)
        run = self.session.query(db.PipelineRun).get(self.run_id)
        assert run.verified == 1

    def test_mark_run_verified_false(self):
        import database as db
        db.mark_run_verified(self.session, self.run_id, False)
        run = self.session.query(db.PipelineRun).get(self.run_id)
        assert run.verified == 0

    def test_mark_run_verified_nonexistent(self):
        """Should not raise for missing run_id."""
        import database as db
        db.mark_run_verified(self.session, 9999, True)  # no-op, no crash

    def test_get_latest_successful_runs(self):
        import database as db
        runs = db.get_latest_successful_runs(self.session, ["ISSUE-1"])
        assert len(runs) == 1
        assert runs[0].issue_key == "ISSUE-1"

    def test_get_latest_successful_runs_no_match(self):
        import database as db
        runs = db.get_latest_successful_runs(self.session, ["NONEXISTENT"])
        assert len(runs) == 0

    def test_analytics_includes_verification_stats(self):
        import database as db

        # Before verification
        analytics = db.get_analytics(self.session)
        assert analytics["pending_verification"] == 1  # 1 SUCCESS run, not yet verified
        assert analytics["verified"] == 0
        assert analytics["verification_failed"] == 0

        # After verification
        db.mark_run_verified(self.session, self.run_id, True)
        analytics = db.get_analytics(self.session)
        assert analytics["verified"] == 1
        assert analytics["pending_verification"] == 0


# ============================================================================
# 3. Coordinator.verify_fixes tests
# ============================================================================

class TestCoordinatorVerification:
    """Tests for the Coordinator.verify_fixes method."""

    def _make_coordinator(self, sonar_client, db_session=None):
        """Create a coordinator with mocked agents."""
        with patch("agents.coordinator.FixerAgent"), \
             patch("agents.coordinator.TesterAgent"), \
             patch("agents.coordinator.ReviewerAgent"), \
             patch("agents.coordinator.EvaluatorAgent"):
            from agents.coordinator import Coordinator
            return Coordinator(
                sonar_client=sonar_client,
                model_name="test-model",
                url="http://localhost",
                token="test",
                repo_path="/fake/repo",
                db_session=db_session,
            )

    def test_verify_no_issues(self):
        """Empty fixed_issue_keys → immediate SUCCESS."""
        mock_client = MagicMock()
        coord = self._make_coordinator(mock_client)

        result = coord.verify_fixes("my-project", [])
        assert result["status"] == "SUCCESS"
        assert result["verified"] == []
        assert result["still_open"] == []
        mock_client.run_scan_and_wait.assert_not_called()

    def test_verify_all_fixed(self):
        """All fixed issues are gone after re-scan → SUCCESS."""
        mock_client = MagicMock()
        mock_client.run_scan_and_wait.return_value = True
        # Post-scan returns NO issues at all
        mock_client.get_issues.return_value = []

        coord = self._make_coordinator(mock_client)
        result = coord.verify_fixes("my-project", ["ISSUE-1", "ISSUE-2"])

        assert result["status"] == "SUCCESS"
        assert set(result["verified"]) == {"ISSUE-1", "ISSUE-2"}
        assert result["still_open"] == []
        assert result["new_issues"] == 0

    def test_verify_partial(self):
        """Some issues gone, some still open → PARTIAL."""
        mock_client = MagicMock()
        mock_client.run_scan_and_wait.return_value = True
        # Post-scan still has ISSUE-2
        mock_client.get_issues.return_value = [
            {"key": "ISSUE-2", "rule": "python:S999", "component": "proj:foo.py"},
        ]

        coord = self._make_coordinator(mock_client)
        result = coord.verify_fixes("my-project", ["ISSUE-1", "ISSUE-2"])

        assert result["status"] == "PARTIAL"
        assert result["verified"] == ["ISSUE-1"]
        assert result["still_open"] == ["ISSUE-2"]

    def test_verify_none_fixed(self):
        """All issues still open → FAILED."""
        mock_client = MagicMock()
        mock_client.run_scan_and_wait.return_value = True
        mock_client.get_issues.return_value = [
            {"key": "ISSUE-1"}, {"key": "ISSUE-2"},
        ]

        coord = self._make_coordinator(mock_client)
        result = coord.verify_fixes("my-project", ["ISSUE-1", "ISSUE-2"])

        assert result["status"] == "FAILED"
        assert result["verified"] == []
        assert set(result["still_open"]) == {"ISSUE-1", "ISSUE-2"}

    def test_verify_scan_failure(self):
        """Scan raises exception → FAILED with error message."""
        mock_client = MagicMock()
        mock_client.run_scan_and_wait.side_effect = Exception("Scanner crashed")

        coord = self._make_coordinator(mock_client)
        result = coord.verify_fixes("my-project", ["ISSUE-1"])

        assert result["status"] == "FAILED"
        assert "Scanner crashed" in result["message"]
        assert result["still_open"] == ["ISSUE-1"]

    def test_verify_detects_new_issues(self):
        """Post-scan has issues not in the fixed set → counted as new_issues."""
        mock_client = MagicMock()
        mock_client.run_scan_and_wait.return_value = True
        mock_client.get_issues.return_value = [
            {"key": "NEW-1"}, {"key": "NEW-2"},
        ]

        coord = self._make_coordinator(mock_client)
        result = coord.verify_fixes("my-project", ["ISSUE-1"])

        assert result["status"] == "SUCCESS"  # ISSUE-1 is gone
        assert result["verified"] == ["ISSUE-1"]
        assert result["new_issues"] == 2


# ============================================================================
# 4. FastAPI endpoint tests
# ============================================================================

class TestVerifyEndpoint:
    """Tests for POST /pipeline/verify."""

    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up the FastAPI test client."""
        # Patch env vars before importing the app
        with patch.dict(os.environ, {
            "SONARQUBE_URL": "http://sonarqube:9000",
            "SONARQUBE_TOKEN": "test-token",
            "LLM_MODEL": "test-model",
            "LLM_BASE_URL": "http://localhost",
            "LLM_API_KEY": "test-key",
        }):
            from fastapi.testclient import TestClient
            from api import app
            self.client = TestClient(app)
            yield

    def test_verify_missing_both_repo_fields(self):
        """Should 400 if neither repo_url nor repo_path provided."""
        resp = self.client.post("/pipeline/verify", json={
            "project_key": "test",
            "issue_keys": ["ISSUE-1"],
        })
        assert resp.status_code == 400

    def test_verify_nonexistent_repo_path(self):
        """Should 400 if repo_path doesn't exist."""
        resp = self.client.post("/pipeline/verify", json={
            "repo_path": "/nonexistent/path",
            "project_key": "test",
            "issue_keys": ["ISSUE-1"],
        })
        assert resp.status_code == 400

    @patch("api.Coordinator")
    @patch("api.SonarCubeClient")
    @patch("api.db")
    def test_verify_success(self, mock_db, mock_sonar_cls, mock_coord_cls, tmp_path):
        """Successful verification returns 200 with results."""
        # Create a real directory for repo_path
        repo = tmp_path / "test-repo"
        repo.mkdir()

        mock_session = MagicMock()
        mock_db.get_session.return_value = mock_session

        mock_coord = MagicMock()
        mock_coord.verify_fixes.return_value = {
            "status": "SUCCESS",
            "verified": ["ISSUE-1"],
            "still_open": [],
            "new_issues": 0,
            "message": "All verified!",
        }
        mock_coord_cls.return_value = mock_coord

        resp = self.client.post("/pipeline/verify", json={
            "repo_path": str(repo),
            "project_key": "test",
            "issue_keys": ["ISSUE-1"],
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["verified"] == ["ISSUE-1"]
        assert data["still_open"] == []
