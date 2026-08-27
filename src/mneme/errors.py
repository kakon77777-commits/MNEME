class MnemeError(Exception):
    """Base MNEME error."""


class CanonicalizationError(MnemeError, ValueError):
    """Input cannot be represented by the canonical JSON contract."""
