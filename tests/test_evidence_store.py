from api.evidence_store import EvidencePackStore, EvidenceStoreError
from api.schemas import EvidenceItem, EvidencePack, Source
import pytest


def make_pack(statement="fact"):
    return EvidencePack(
        evidence_pack_id="ep-1",
        items=[EvidenceItem(evidence_id="ev-1", source_id="src-1", statement=statement)],
        sources=[Source(source_id="src-1", uri="https://example.test/source")],
    )


def test_put_get_roundtrip_and_copy_isolation():
    store = EvidencePackStore()
    store.put(make_pack())
    fetched = store.get("ep-1")
    assert fetched.items[0].statement == "fact"
    fetched.items[0].statement = "mutated"
    assert store.get("ep-1").items[0].statement == "fact"


def test_same_id_same_payload_is_idempotent():
    store = EvidencePackStore()
    store.put(make_pack())
    store.put(make_pack())
    assert len(store) == 1


def test_same_id_different_payload_fails_closed():
    store = EvidencePackStore()
    store.put(make_pack("fact-a"))
    with pytest.raises(EvidenceStoreError, match="collision"):
        store.put(make_pack("fact-b"))


def test_unknown_pack_fails_closed():
    store = EvidencePackStore()
    with pytest.raises(EvidenceStoreError, match="not found"):
        store.get("missing")
