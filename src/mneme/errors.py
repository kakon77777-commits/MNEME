class MnemeError(Exception):
    """Base MNEME error."""


class CanonicalizationError(MnemeError, ValueError):
    """Input cannot be represented by the canonical JSON contract."""


class RecordValidationError(MnemeError, ValueError):
    """A memory record violates the MLF-RM/0.1 contract."""


class TransactionValidationError(MnemeError, ValueError):
    """A transaction is incomplete, stale, or inconsistent."""
