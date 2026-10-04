import pytest

from api.versioning import ContentVersionStore, VersioningError


def test_initial_and_multiple_revisions_preserve_lineage():
    store = ContentVersionStore()
    v1 = store.create_initial_version("task-a", "one", evidence_pack_id="pack-1", claim_ids=["c1"])
    v2 = store.create_revision(v1.content_version_id, "two")
    v3 = store.create_revision(v2.content_version_id, "three", claim_ids=["c2"])
    assert v1.parent_version_id is None and v2.parent_version_id == v1.content_version_id
    assert v3.parent_version_id == v2.content_version_id
    assert [v.content for v in store.get_history("task-a")] == ["one", "two", "three"]
    assert store.get_version(v1.content_version_id).content == "one"


def test_revision_isolates_claim_lists_and_allows_evidence_update():
    store = ContentVersionStore()
    v1 = store.create_initial_version("task-a", "one", evidence_pack_id="p1", claim_ids=["c1"])
    v2 = store.create_revision(v1.content_version_id, "two", evidence_pack_id="p2", claim_ids=["c2"])
    v2.claim_ids.append("c3")
    assert v1.claim_ids == ["c1"]
    assert v2.evidence_pack_id == "p2"


def test_missing_parent_and_cross_task_revision_fail_closed():
    store = ContentVersionStore()
    with pytest.raises(VersioningError, match="version not found"):
        store.create_revision("missing", "x")
    v1 = store.create_initial_version("task-a", "one")
    with pytest.raises(VersioningError, match="does not match"):
        store.create_revision(v1.content_version_id, "x", task_id="task-b")


def test_history_isolated_by_task():
    store = ContentVersionStore()
    store.create_initial_version("task-a", "a")
    store.create_initial_version("task-b", "b")
    assert [v.content for v in store.get_history("task-a")] == ["a"]
    assert [v.content for v in store.get_history("task-b")] == ["b"]


def test_branching_history_and_actual_lineages():
    store = ContentVersionStore()
    v1 = store.create_initial_version("task-a", "one")
    v2 = store.create_revision(v1.content_version_id, "two")
    v2b = store.create_revision(v1.content_version_id, "two-b")
    v3 = store.create_revision(v2.content_version_id, "three")
    assert [v.content for v in store.get_history("task-a")] == ["one", "two", "two-b", "three"]
    assert [v.content for v in store.get_lineage(v3.content_version_id)] == ["one", "two", "three"]
    assert [v.content for v in store.get_lineage(v2b.content_version_id)] == ["one", "two-b"]
