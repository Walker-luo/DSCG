"""CLI result locations; explicit backend folders with read-in-place legacy resume.

New runs are written to ``<root>/<backend>/<model>/<name>/`` so a model's runs stay
grouped together. Older layouts are still resolved on resume and never moved.
"""
from pathlib import Path
import re


def safe_result_component(value, fallback):
    component = re.sub(r'[^\w.-]+', '-', str(value or '').strip(), flags=re.UNICODE)
    return component.strip(' .-_') or fallback


def run_component(model_id, run_name, *, default_name=None):
    """Flat run label, used for pipeline/report naming rather than for paths."""
    if run_name is None or not str(run_name).strip():
        return safe_result_component(default_name or model_id, 'run')
    return safe_result_component(model_id, 'model') + '_' + safe_result_component(run_name, 'run')


def run_relative(model_id, run_name, *, default_name=None):
    """Relative run path: ``<model>/<name>``; an unnamed run stays a single folder."""
    if run_name is None or not str(run_name).strip():
        return Path(safe_result_component(default_name or model_id, 'run'))
    return Path(safe_result_component(model_id, 'model')) / safe_result_component(run_name, 'run')


def resolve_run_path(root, backend_id, model_id, run_name, *, default_name=None, allow_legacy=False):
    """Return a location without creating, moving or inspecting run contents.

    An existing new path always wins, including an incomplete directory or a
    dangling symlink. Callers validate its bindings and never fall back on error.
    """
    if backend_id not in {'agentdojo', 'agentdyn'}:
        raise ValueError('unknown benchmark backend for result path')
    root = Path(root)
    new = root / backend_id / run_relative(model_id, run_name, default_name=default_name)
    if not allow_legacy or new.exists() or new.is_symlink():
        return new
    # Previous layout: <backend>/<model>_<name>, then <model>_<backend>_<name>.
    flat = root / backend_id / run_component(model_id, run_name, default_name=default_name)
    if flat.exists() or flat.is_symlink():
        return flat
    if run_name is None or not str(run_name).strip():
        legacy_name = f'{default_name or model_id}_{backend_id}'
    else:
        legacy_name = (safe_result_component(model_id, 'model') + '_' + backend_id + '_'
                       + safe_result_component(run_name, 'run'))
    legacy = root / legacy_name
    return legacy if legacy.exists() or legacy.is_symlink() else new


def result_layout(root, backend_id, base):
    base, backend_root = Path(base), Path(root) / backend_id
    if base.parent == backend_root:
        return 'backend/model_run/attack/suite'
    if base.parent != backend_root and base.parent.parent == backend_root:
        return 'backend/model/name/attack/suite'
    return 'model_run/attack/suite'
