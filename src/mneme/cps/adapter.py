from __future__ import annotations

from typing import Iterable, Sequence

from ..errors import CpsValidationError
from ..records import MemoryRecord
from .factorization import FactorizationProposal, build_factorization_proposal
from .models import EquivalenceContract, PersistenceAssessment, RecomputationReference
from .rules import AssessmentContext, assess_record
from .seed import CognitiveSeedProposal, build_cognitive_seed_proposal


class CpsObservationAdapter:
    """Read-only composition surface for CPS/0.1 observation workflows."""

    def assess(
        self,
        records: Sequence[MemoryRecord],
        contexts: Sequence[AssessmentContext],
    ) -> tuple[PersistenceAssessment, ...]:
        if len(records) != len(contexts):
            raise CpsValidationError("records and contexts must have identical lengths")
        return tuple(assess_record(record, context) for record, context in zip(records, contexts))

    def factorize(
        self,
        *,
        assessments: Iterable[PersistenceAssessment],
        source_refs: list[str],
        anchors: list[str],
        structure: list[dict[str, object]],
        generators: list[dict[str, object]],
        obligations: list[dict[str, object]],
        provenance_refs: list[str],
        recompute_refs: list[str],
        unresolved_refs: list[str],
    ) -> FactorizationProposal:
        return build_factorization_proposal(
            assessments=assessments,
            source_refs=source_refs,
            anchors=anchors,
            structure=structure,
            generators=generators,
            obligations=obligations,
            provenance_refs=provenance_refs,
            recompute_refs=recompute_refs,
            unresolved_refs=unresolved_refs,
        )

    def propose_seed(
        self,
        *,
        factorization: FactorizationProposal,
        anchors: list[str],
        structure: list[dict[str, object]],
        generators: list[dict[str, object]],
        obligations: list[dict[str, object]],
        provenance_refs: list[str],
        recomputation_refs: Iterable[RecomputationReference],
        unresolved_components: list[str],
        equivalence_contract: EquivalenceContract | None,
    ) -> CognitiveSeedProposal:
        return build_cognitive_seed_proposal(
            factorization=factorization,
            anchors=anchors,
            structure=structure,
            generators=generators,
            obligations=obligations,
            provenance_refs=provenance_refs,
            recomputation_refs=recomputation_refs,
            unresolved_components=unresolved_components,
            equivalence_contract=equivalence_contract,
        )
