from typing import Any


def set_path(data: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """Set a dotted-path field in place (or remove it, if value is ...)."""
    *parents, leaf = path.split(".")
    target = data
    for key in parents:
        target = target[key]
    if value is ...:
        del target[leaf]
    else:
        target[leaf] = value
    return data
