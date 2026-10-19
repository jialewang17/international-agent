import pytest

from api.schemas import Claim
from api.claim_store import ClaimStore, ClaimStoreError


def c(claim_id="clm_1", text="苏绣是传统工艺。", ids=None):
    return Claim(
        claim_id=claim_id,
        text=text,
        evidence_ids=list(ids or []),
    )


def test_put_get_defensive_copies():
    store = ClaimStore()
    original = c(ids=["ev_1"])
    returned = store.put("ep_a", original)

    assert returned == original
    assert returned is not original

    original.evidence_ids.append("ev_2")
    returned.evidence_ids.append("ev_3")

    stored = store.get("ep_a", "clm_1")
    assert stored.evidence_ids == ["ev_1"]

    stored.text = "tampered"
    assert store.get("ep_a", "clm_1").text == "苏绣是传统工艺。"


def test_get_missing_is_none():
    assert ClaimStore().get("ep_a", "clm_missing") is None


def test_idempotent_put_and_collision():
    store = ClaimStore()
    first = c(ids=["ev_1"])

    store.put("ep_a", first)
    assert store.put("ep_a", c(ids=["ev_1"])) == first
    assert len(store) == 1

    with pytest.raises(ClaimStoreError, match="claim collision"):
        store.put("ep_a", c(ids=["ev_2"]))

    with pytest.raises(ClaimStoreError, match="claim collision"):
        store.put("ep_a", c(text="另一句话", ids=["ev_1"]))

    assert store.get("ep_a", "clm_1") == first


def test_equal_id_different_pack_independent():
    store = ClaimStore()
    store.put("ep_a", c(ids=["ev_a"]))
    store.put("ep_b", c(ids=["ev_b"]))

    assert len(store) == 2
    assert store.get("ep_a", "clm_1").evidence_ids == ["ev_a"]
    assert store.get("ep_b", "clm_1").evidence_ids == ["ev_b"]


def test_put_many_order_idempotence_and_output_snapshots():
    store = ClaimStore()
    many = [
        c("clm_2", "句子二"),
        c("clm_1", "句子一"),
        c("clm_2", "句子二"),
    ]

    result = store.put_many("ep_a", many)

    assert [x.claim_id for x in result] == [
        "clm_2", "clm_1", "clm_2"
    ]
    assert len(store) == 2
    assert result[0] is not result[2]

    result[0].text = "changed"
    assert store.get("ep_a", "clm_2").text == "句子二"
    assert [x.claim_id for x in store.all("ep_a")] == [
        "clm_1", "clm_2"
    ]


def test_put_many_atomic_conflict_against_storage():
    store = ClaimStore()
    store.put("ep_a", c("clm_1", "原句", ["ev_1"]))

    with pytest.raises(ClaimStoreError, match="claim collision"):
        store.put_many(
            "ep_a",
            [
                c("clm_new", "新句"),
                c("clm_1", "原句", ["ev_2"]),
            ],
        )

    assert store.get("ep_a", "clm_new") is None
    assert len(store) == 1


def test_put_many_atomic_intrabatch_conflict():
    store = ClaimStore()

    with pytest.raises(ClaimStoreError, match="claim collision"):
        store.put_many(
            "ep_a",
            [
                c("clm_1", "一"),
                c("clm_2", "二"),
                c("clm_1", "不同"),
            ],
        )

    assert len(store) == 0


def test_put_many_atomic_invalid_claim():
    store = ClaimStore()

    with pytest.raises(ClaimStoreError, match="claim must be"):
        store.put_many(
            "ep_a",
            [c("clm_1", "一"), object()],
        )

    assert len(store) == 0


def test_get_many_missing_fails_closed():
    store = ClaimStore()
    store.put("ep_a", c())

    with pytest.raises(ClaimStoreError, match="missing claim"):
        store.get_many(
            "ep_a",
            ["clm_1", "clm_missing"],
        )


def test_get_many_order_duplicates_and_copy():
    store = ClaimStore()
    store.put_many(
        "ep_a",
        [c("clm_1", "一"), c("clm_2", "二")],
    )

    out = store.get_many(
        "ep_a",
        ["clm_2", "clm_1", "clm_2"],
    )

    assert [x.claim_id for x in out] == [
        "clm_2", "clm_1", "clm_2"
    ]
    assert out[0] is not out[2]

    out[0].text = "modified"
    assert store.get("ep_a", "clm_2").text == "二"


def test_all_pack_local_sorted_and_copy():
    store = ClaimStore()
    store.put("ep_b", c("clm_3", "三"))
    store.put("ep_a", c("clm_2", "二"))
    store.put("ep_a", c("clm_1", "一"))

    assert [x.claim_id for x in store.all("ep_a")] == [
        "clm_1", "clm_2"
    ]
    assert [x.claim_id for x in store.all("ep_b")] == [
        "clm_3"
    ]
    assert store.all("ep_c") == []

    got = store.all("ep_a")
    got[0].text = "modified"
    assert store.get("ep_a", "clm_1").text == "一"


def test_empty_batches():
    store = ClaimStore()

    assert store.put_many("ep_a", []) == []
    assert store.get_many("ep_a", []) == []
    assert len(store) == 0


@pytest.mark.parametrize("pack", [
    None, "", " ", 123, [], {}
])
def test_bad_pack_id(pack):
    store = ClaimStore()

    with pytest.raises(ClaimStoreError):
        store.put(pack, c())

    with pytest.raises(ClaimStoreError):
        store.put_many(pack, [])

    with pytest.raises(ClaimStoreError):
        store.get(pack, "clm_1")

    with pytest.raises(ClaimStoreError):
        store.get_many(pack, [])

    with pytest.raises(ClaimStoreError):
        store.all(pack)


@pytest.mark.parametrize("bad", [
    None, "", " ", 123
])
def test_bad_claim_id(bad):
    store = ClaimStore()

    with pytest.raises(ClaimStoreError):
        store.get("ep_a", bad)

    with pytest.raises(ClaimStoreError):
        store.get_many("ep_a", [bad])


@pytest.mark.parametrize("bad", [
    None, "str", 123
])
def test_invalid_batch_iterables(bad):
    store = ClaimStore()

    with pytest.raises(ClaimStoreError):
        store.put_many("ep_a", bad)

    with pytest.raises(ClaimStoreError):
        store.get_many("ep_a", bad)


def test_invalid_mutated_claim_rejected():
    store = ClaimStore()
    cl = c()

    cl.claim_id = " "
    with pytest.raises(ClaimStoreError):
        store.put("ep_a", cl)

    cl.claim_id = "clm_1"
    cl.text = ""
    with pytest.raises(ClaimStoreError):
        store.put("ep_a", cl)

    cl.text = "valid"
    cl.evidence_ids = [" "]
    with pytest.raises(ClaimStoreError):
        store.put("ep_a", cl)

    assert len(store) == 0


def test_interop_with_i2b001_extractor():
    from api.claim_extraction import DeterministicClaimExtractor

    claims = DeterministicClaimExtractor().extract(
        "苏绣是传统工艺。"
    )

    assert len(claims) == 1
    assert claims[0].evidence_ids == []

    store = ClaimStore()
    assert store.put_many("ep_suzhou", claims) == claims
    assert store.get_many(
        "ep_suzhou",
        [claims[0].claim_id],
    ) == claims
