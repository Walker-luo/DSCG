"""CLI result locations; explicit backend folders with read-in-place legacy resume."""
from pathlib import Path
import re


def safe_result_component(value, fallback):
    component = re.sub(r'[^\w.-]+', '-', str(value or '').strip(), flags=re.UNICODE)
    return component.strip(' .-_') or fallback


def run_component(model_id, run_name, *, default_name=None):
    if run_name is None or not str(run_name).strip():
        return safe_result_component(default_name or model_id, 'run')
    return safe_result_component(model_id, 'model') + '_' + safe_result_component(run_name, 'run')


def resolve_run_path(root, backend_id, model_id, run_name, *, default_name=None, allow_legacy=False):
    """Return a location without creating, moving or inspecting run contents.

    An existing new path always wins, including an incomplete directory or a
    dangling symlink. Callers validate its bindings and never fall back on error.
    """
    if backend_id not in {'agentdojo', 'agentdyn'}:
        raise ValueError('unknown benchmark backend for result path')
    root = Path(root)
    new = root / backend_id / run_component(model_id, run_name, default_name=default_name)
    if not allow_legacy or new.exists() or new.is_symlink():
        return new
    if run_name is None or not str(run_name).strip():
        legacy_name = f'{default_name or model_id}_{backend_id}'
    else:
        legacy_name = (safe_result_component(model_id, 'model') + '_' + backend_id + '_'
                       + safe_result_component(run_name, 'run'))
    legacy = root / legacy_name
    return legacy if legacy.exists() or legacy.is_symlink() else new


def result_layout(root, backend_id, base):
    return ('backend/model_run/attack/suite' if Path(base).parent == Path(root) / backend_id
            else 'model_run/attack/suite')
