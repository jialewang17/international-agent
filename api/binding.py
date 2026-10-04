"""集中执行 Claim -> Evidence -> Source 的最小可追溯绑定校验。"""
from typing import Any, Dict, List

from api.schemas import Claim, EvidencePack


class BindingError(ValueError):
    """Raised when a provenance reference cannot be resolved."""


def resolve_claim_trace(claim: Claim, pack: EvidencePack) -> Dict[str, Any]:
    evidence_by_id = {item.evidence_id: item for item in pack.items}
    source_by_id = {source.source_id: source for source in pack.sources}
    refs = list(dict.fromkeys(claim.evidence_refs))
    if not refs:
        return {"status": "unbound", "claim_id": claim.claim_id, "evidence": [], "sources": []}

    missing_evidence = [ref for ref in refs if ref not in evidence_by_id]
    if missing_evidence:
        raise BindingError(f"missing evidence: {', '.join(missing_evidence)}")

    evidence_trace: List[Dict[str, Any]] = []
    source_ids: List[str] = []
    for evidence_id in refs:
        item = evidence_by_id[evidence_id]
        if not item.source_id or item.source_id not in source_by_id:
            raise BindingError(f"missing source for evidence: {evidence_id}")
        if item.source_id not in source_ids:
            source_ids.append(item.source_id)
        for span in item.spans:
            if not span.source_id or span.source_id not in source_by_id:
                raise BindingError(f"missing source for span: {span.span_id}")
            if span.source_id not in source_ids:
                source_ids.append(span.source_id)
        evidence_trace.append(item.model_dump(mode="json"))

    return {
        "status": "traceable",
        "claim_id": claim.claim_id,
        "evidence": evidence_trace,
        "sources": [source_by_id[s].model_dump(mode="json") for s in source_ids],
    }
