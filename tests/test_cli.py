
import pytest
import os
import signal
import time
import json
import psutil
from unittest.mock import patch, MagicMock
from pathlib import Path
from mitschreiber.cli import main, _active_path
from mitschreiber.session import run_session

@pytest.fixture
def mock_session_dir(tmp_path):
    with patch("mitschreiber.cli.SESSIONS_DIR", tmp_path), \
         patch("mitschreiber.session.SESSIONS_DIR", tmp_path), \
         patch("mitschreiber.paths.SESS_DIR", tmp_path):
        yield tmp_path

def test_status_no_active_session(mock_session_dir, capsys):
    with patch("sys.argv", ["mitschreiber", "status"]):
        main()
    captured = capsys.readouterr()
    assert "No active session." in captured.out

@patch("psutil.Process")
def test_status_active_session(mock_process_cls, mock_session_dir, capsys):
    active_file = mock_session_dir / "active.json"
    pid = 12345
    active_data = {"session_id": "test-id", "pid": pid, "flags": {}}
    active_file.write_text(json.dumps(active_data))

    # Mock the process to exist and be valid
    mock_proc = MagicMock()
    mock_proc.status.return_value = psutil.STATUS_RUNNING
    mock_proc.cmdline.return_value = ["/path/to/python", "mitschreiber"]
    mock_process_cls.return_value = mock_proc

    with patch("sys.argv", ["mitschreiber", "status"]):
        main()
    captured = capsys.readouterr()
    assert '"session_id": "test-id"' in captured.out

@patch("mitschreiber.cli.run_session")
def test_start_creates_session_file(mock_run, mock_session_dir, capsys):
    # Mock run_session to just return immediately
    mock_run.side_effect = None

    with patch("sys.argv", ["mitschreiber", "start"]):
        main()

    # Check that run_session was called, implying the flow reached there.
    # The session file is created before run_session and removed in finally.
    mock_run.assert_called_once()
    captured = capsys.readouterr()
    assert "Session stopped." in captured.out

@patch("os.kill")
@patch("psutil.Process")
def test_stop_sends_signal(mock_process_cls, mock_kill, mock_session_dir, capsys):
    active_file = mock_session_dir / "active.json"
    pid = 12345
    active_data = {"session_id": "test-id", "pid": pid, "flags": {}}
    active_file.write_text(json.dumps(active_data))

    mock_proc = MagicMock()
    mock_proc.cmdline.return_value = ["/path/to/python", "mitschreiber"]
    mock_process_cls.return_value = mock_proc

    with patch("sys.argv", ["mitschreiber", "stop"]):
        main()

    mock_kill.assert_called_with(pid, signal.SIGINT)
    # Note: We no longer assert that active_file is gone, because 'stop' command
    # delegates cleanup to the receiving process. In this test, the process is mocked
    # and doesn't actually run/die, so the file remains.
    # assert not active_file.exists()
    captured = capsys.readouterr()
    assert f"Sent SIGINT to PID {pid}" in captured.out


def test_status_handles_disappearing_active_file(monkeypatch, capsys):
    fake_path = MagicMock()
    fake_path.exists.return_value = True
    fake_path.read_text.side_effect = FileNotFoundError

    monkeypatch.setattr("mitschreiber.cli._active_path", lambda: fake_path)

    main(["status"])

    captured = capsys.readouterr()
    assert "No active session." in captured.out


def test_stop_handles_corrupt_active_file(mock_session_dir, capsys):
    active_file = mock_session_dir / "active.json"
    active_file.write_text("not-json")

    with patch("sys.argv", ["mitschreiber", "stop"]):
        main()

    captured = capsys.readouterr()
    assert "No active session." in captured.out
    assert not active_file.exists()


def test_stop_handles_missing_pid(mock_session_dir, capsys):
    active_file = mock_session_dir / "active.json"
    active_file.write_text(json.dumps({"session_id": "abc", "flags": {}}))

    with patch("sys.argv", ["mitschreiber", "stop"]):
        main()

    captured = capsys.readouterr()
    assert "No active session." in captured.out
    assert not active_file.exists()


def test_stop_cleans_stale_process_file(mock_session_dir, capsys):
    active_file = mock_session_dir / "active.json"
    pid = 43210
    active_file.write_text(json.dumps({"session_id": "abc", "pid": pid, "flags": {}}))

    with (
        patch("psutil.Process", side_effect=psutil.NoSuchProcess(pid, "dead")),
        patch("sys.argv", ["mitschreiber", "stop"]),
    ):
        main()

    captured = capsys.readouterr()
    assert "Stale session file." in captured.out
    assert not active_file.exists()


def test_stop_cleans_stale_session_on_access_denied(mock_session_dir, capsys):
    """
    If psutil.Process() raises AccessDenied, it means the PID belongs to another user/root,
    so it cannot be our session. The session file is stale.
    """
    active_file = mock_session_dir / "active.json"
    pid = 99999
    active_file.write_text(json.dumps({"session_id": "abc", "pid": pid, "flags": {}}))

    with (
        patch("psutil.Process", side_effect=psutil.AccessDenied(pid)),
        patch("sys.argv", ["mitschreiber", "stop"]),
    ):
        main()

    captured = capsys.readouterr()

    # Verify we get the permission denied message (which is current behavior)
    # BUT we also want to verify the file is gone (desired fix).
    # Currently this will FAIL because the file is not removed.
    assert not active_file.exists(), "Stale session file should be removed on AccessDenied"
