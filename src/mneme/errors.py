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


class StoreWriterBusyError(StoreConflictError):
    """Another writer currently holds the store's single-writer lock."""


class RecordIdConflictError(StoreConflictError):
    """A transaction reuses a record ID in canonical history."""


class StoreIntegrityError(MnemeError, RuntimeError):
    """Canonical store bytes or causal metadata failed integrity checks."""


class RouteValidationError(MnemeError, ValueError):
    """A route declaration violates the MLF-RM/0.1 route contract."""


class ProjectionBudgetError(MnemeError, ValueError):
    """A projection cannot satisfy its hard materialization budget."""


class ProfileValidationError(MnemeError, ValueError):
    """A memory Markdown compatibility profile is invalid or ambiguous."""


class ClaudeContractError(MnemeError, ValueError):
    """A Claude global-memory transition contract is invalid or unsealed."""


class ManualAuthorityError(ClaudeContractError):
    """A local manual-write authorization is invalid or ineligible."""


class ClaudeRouteError(ClaudeContractError):
    """A Claude projection request or route is stale or outside the global profile."""


class RequiredRecordOmittedError(ClaudeContractError):
    """A required global record was omitted from a bounded Claude projection."""


class CpsValidationError(MnemeError, ValueError):
    """A Cognitive Persistence Semantics object violates the CPS/0.1 contract."""
