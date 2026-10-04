from poolrouter.runtime.models import ALIASES


def providers_for_alias(alias: str) -> tuple[str, ...]:
    """Stable candidate order. Admission removes ineligible providers."""
    return ALIASES.get(alias, ())
