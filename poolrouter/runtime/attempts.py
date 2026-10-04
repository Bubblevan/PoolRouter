from poolrouter.runtime.errors import FALLBACK_CATEGORIES, ProviderFailure


def may_fallback(failure: ProviderFailure) -> bool:
    return failure.category in FALLBACK_CATEGORIES
