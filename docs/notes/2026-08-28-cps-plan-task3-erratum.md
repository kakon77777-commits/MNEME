# MNEME-CPS/0.1 Implementation Plan — Task 3 Erratum

Date: 2026-08-28

The Task 3 illustrative failing test in `docs/superpowers/plans/2026-08-28-cognitive-persistence-semantics.md` conflicts with the detailed rule immediately below it.

The normative rule is:

```text
Every required preservation must be explicitly covered by at least one of:
- anchors
- provenance_refs
- unresolved_refs
```

Therefore a proposal that includes a required preservation in `provenance_refs` is valid with respect to the evidential-floor coverage rule and must not fail merely because the same reference is absent from `anchors`.

The correct negative case has the required preservation absent from all three coverage sets.

The CPS/0.1 implementation follows this normative rule because it matches the canonical design's evidential-floor principle: exact evidence may remain preserved and addressable by provenance reference without duplicating its content as an anchor.

This erratum changes no runtime semantics beyond resolving the plan example in favor of the already stated formal rule.
