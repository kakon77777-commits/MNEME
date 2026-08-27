class MnemeError(Exception):
    """Base MNEME error."""


class CanonicalizationError(MnemeError, ValueError):
    """Input cannot be represented by the canonical JSON contract."""


class RecordValidationError(MnemeError, ValueError):
    """A memory record violates the MLF-RM/0.1 contract."""


class TransactionValidationError(MnemeError, ValueError):
    """A transaction is incomplete, stale, or inconsistent."""


class StoreConflictError(MnemeError, RuntimeError):
    """A store write conflicts with the current canonical head."""


class StoreIntegrityError(MnemeError, RuntimeError):
    """Canonical store bytes or causal metadata failed integrity checks."""


class RouteValidationError(MnemeError, ValueError):
    """A route declaration violates the MLF-RM/0.1 route contract."""


class ProjectionBudgetError(MnemeError, ValueError):
    """A projection cannot satisfy its hard materialization budget."""
