"""Backend-independent native trace paths for historical and flat layouts."""
from pathlib import Path


def trace_path(suite_dir, user, attack, injection, *, goal=False):
    """Read the flat layout first, retaining historical native cache fallback."""
    suite_dir = Path(suite_dir)
    flat = suite_dir / (f'{user}.json' if goal else f'{user}/{injection or "none"}.json')
    legacy = suite_dir / str(user) / str(attack) / f'{injection or "none"}.json'
    return flat if flat.exists() or not legacy.exists() else legacy

