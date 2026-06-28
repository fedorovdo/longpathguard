from __future__ import annotations

from app import watcher


class BrokenObserver:
    def __init__(self) -> None:
        self.stop_called = False

    def schedule(self, *_args, **_kwargs) -> None:
        return None

    def start(self) -> None:
        raise OSError("observer start failed")

    def stop(self) -> None:
        self.stop_called = True

    def is_alive(self) -> bool:
        return False


def test_observer_start_failure_is_contained(tmp_path, monkeypatch) -> None:
    broken = BrokenObserver()
    monkeypatch.setattr(watcher, "Observer", lambda: broken)
    manager = watcher.WatcherManager(
        {"watcher": {"root_path": str(tmp_path), "excluded_paths": []}}
    )

    assert manager.start() is False
    assert manager.error_code == "watcher_start_failed"
    assert manager.is_running is False
    assert broken.stop_called is True
