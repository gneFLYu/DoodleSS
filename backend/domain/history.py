"""Bounded project snapshot history for transactional undo and redo."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Project, project_from_dict, project_to_dict


HISTORY_LIMIT = 100


@dataclass
class HistoryEntry:
    label: str
    snapshot: dict[str, Any]


@dataclass
class ProjectHistory:
    undo: list[HistoryEntry] = field(default_factory=list)
    redo: list[HistoryEntry] = field(default_factory=list)


_HISTORIES: dict[str, ProjectHistory] = {}


def _history(key: str) -> ProjectHistory:
    return _HISTORIES.setdefault(key, ProjectHistory())


def record_edit(key: str, project: Project, label: str) -> None:
    history = _history(key)
    history.undo.append(HistoryEntry(label=label, snapshot=project_to_dict(project)))
    if len(history.undo) > HISTORY_LIMIT:
        del history.undo[:-HISTORY_LIMIT]
    history.redo.clear()


def undo_edit(key: str, current: Project) -> tuple[Project, str] | None:
    history = _history(key)
    if not history.undo:
        return None
    entry = history.undo.pop()
    history.redo.append(HistoryEntry(label=entry.label, snapshot=project_to_dict(current)))
    restored = project_from_dict(entry.snapshot)
    restored.revision = current.revision
    return restored, entry.label


def redo_edit(key: str, current: Project) -> tuple[Project, str] | None:
    history = _history(key)
    if not history.redo:
        return None
    entry = history.redo.pop()
    history.undo.append(HistoryEntry(label=entry.label, snapshot=project_to_dict(current)))
    restored = project_from_dict(entry.snapshot)
    restored.revision = current.revision
    return restored, entry.label


def history_status(key: str) -> dict[str, Any]:
    history = _history(key)
    return {
        "undo_depth": len(history.undo),
        "redo_depth": len(history.redo),
        "undo_label": history.undo[-1].label if history.undo else None,
        "redo_label": history.redo[-1].label if history.redo else None,
        "undo_stack": [item.label for item in reversed(history.undo)],
        "redo_stack": [item.label for item in reversed(history.redo)],
    }


def clear_history(key: str) -> None:
    _HISTORIES.pop(key, None)
