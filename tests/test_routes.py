from mneme.records import MemoryRecord
from mneme.routes import Route, RouteResolver


def rec(record_id, scope, *, record_type="fact", status="active", text=None):
    kind, _, subject = scope.partition("/")
    return MemoryRecord.from_dict({
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": record_type,
        "scope": {"kind": kind, "subject": subject or "core"},
        "content": {"text": text if text is not None else record_id},
        "relations": [],
        "provenance": {"event_id": f"evt-{record_id}", "source_ref": "synthetic:test"},
        "status": status,
    })


def route(route_id, prefixes, record_types=None):
    return Route.from_dict({
        "route_version": "mneme.route/0.1",
        "route_id": route_id,
        "scope_prefixes": prefixes,
        "record_types": record_types or [],
    })


def test_identity_route_cannot_cross_identity_scope_without_authorization():
    r = route("route://identity/a/bootstrap", ["identity/a"], ["fact"])
    records = [rec("a1", "identity/a"), rec("b1", "identity/b")]
    result = RouteResolver().resolve(r, records, {"identity/a"})
    assert result.included_ids == ("a1",)
    assert any(o.record_id == "b1" and o.reason == "scope_mismatch" for o in result.omitted)


def test_global_route_includes_global_without_explicit_authorization():
    r = route("route://global/tier0", ["global"])
    result = RouteResolver().resolve(r, [rec("g1", "global/core")], set())
    assert result.included_ids == ("g1",)


def test_project_route_excludes_other_project_even_if_other_scope_authorized():
    r = route("route://project/a", ["project/a"], ["fact"])
    records = [rec("a1", "project/a"), rec("b1", "project/b")]
    result = RouteResolver().resolve(r, records, {"project/a", "project/b"})
    assert result.included_ids == ("a1",)
    assert any(o.record_id == "b1" and o.reason == "scope_mismatch" for o in result.omitted)


def test_matching_route_still_requires_private_scope_authorization():
    r = route("route://project/a", ["project/a"])
    result = RouteResolver().resolve(r, [rec("a1", "project/a")], set())
    assert result.included_ids == ()
    assert result.omitted[0].reason == "unauthorized_scope"


def test_type_and_inactive_omissions_are_explained_without_mutation():
    r = route("route://identity/a/bootstrap", ["identity/a"], ["fact"])
    records = [
        rec("ok", "identity/a"),
        rec("lesson", "identity/a", record_type="lesson"),
        rec("inactive", "identity/a", status="withdrawn"),
    ]
    before = [item.to_dict() for item in records]
    result = RouteResolver().resolve(r, records, {"identity/a"})
    assert result.included_ids == ("ok",)
    reasons = {o.record_id: o.reason for o in result.omitted}
    assert reasons == {"lesson": "type_mismatch", "inactive": "inactive"}
    assert [item.to_dict() for item in records] == before
