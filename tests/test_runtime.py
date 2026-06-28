from __future__ import annotations

from types import SimpleNamespace

from app.runtime import activate_config


class FakeWatcher:
    def __init__(self, config, *, starts: bool = True) -> None:
        self.config = config
        self.starts = starts
        self.error = "simulated start failure" if not starts else None
        self.stopped = False

    def start(self) -> bool:
        return self.starts

    def stop(self) -> None:
        self.stopped = True


def make_config(root_path: str) -> dict:
    return {"watcher": {"root_path": root_path, "excluded_paths": []}}


def test_missing_path_does_not_replace_running_watcher(tmp_path) -> None:
    old_config = make_config(str(tmp_path))
    old_watcher = FakeWatcher(old_config)
    state = SimpleNamespace(config=old_config, watcher=old_watcher)
    factory_called = False

    def factory(_config):
        nonlocal factory_called
        factory_called = True
        return FakeWatcher(_config)

    error_code = activate_config(
        state,
        make_config(str(tmp_path / "missing")),
        lambda _config: None,
        factory,
    )

    assert error_code == "path_not_found"
    assert factory_called is False
    assert state.config is old_config
    assert state.watcher is old_watcher
    assert old_watcher.stopped is False


def test_start_failure_does_not_replace_running_watcher(tmp_path) -> None:
    old_config = make_config(str(tmp_path))
    old_watcher = FakeWatcher(old_config)
    state = SimpleNamespace(config=old_config, watcher=old_watcher)
    new_watcher = FakeWatcher(make_config(str(tmp_path)), starts=False)
    saved = False

    def save(_config):
        nonlocal saved
        saved = True

    error_code = activate_config(state, make_config(str(tmp_path)), save, lambda _config: new_watcher)

    assert error_code == "watcher_start_failed"
    assert saved is False
    assert new_watcher.stopped is True
    assert state.config is old_config
    assert state.watcher is old_watcher
    assert old_watcher.stopped is False


def test_config_save_failure_keeps_old_watcher(tmp_path) -> None:
    old_config = make_config(str(tmp_path))
    old_watcher = FakeWatcher(old_config)
    state = SimpleNamespace(config=old_config, watcher=old_watcher)
    new_watcher = FakeWatcher(make_config(str(tmp_path)))

    def fail_save(_config):
        raise OSError("read only")

    error_code = activate_config(state, make_config(str(tmp_path)), fail_save, lambda _config: new_watcher)

    assert error_code == "config_save_failed"
    assert new_watcher.stopped is True
    assert state.config is old_config
    assert state.watcher is old_watcher
    assert old_watcher.stopped is False


def test_successful_switch_stops_old_watcher_after_save(tmp_path) -> None:
    old_config = make_config(str(tmp_path))
    old_watcher = FakeWatcher(old_config)
    state = SimpleNamespace(config=old_config, watcher=old_watcher)
    candidate = make_config(str(tmp_path))
    new_watcher = FakeWatcher(candidate)
    saved = []

    error_code = activate_config(state, candidate, saved.append, lambda _config: new_watcher)

    assert error_code is None
    assert saved == [candidate]
    assert state.config is candidate
    assert state.watcher is new_watcher
    assert old_watcher.stopped is True


def test_empty_root_path_is_safe_at_watcher_start() -> None:
    from app.watcher import WatcherManager

    watcher = WatcherManager(make_config(""))

    assert watcher.start() is False
    assert watcher.error_code == "path_required"
    assert watcher.is_running is False
