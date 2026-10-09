from kompiler.adapters.base import AdapterResult
from kompiler.normalization import normalize_result
from kompiler.protocol.models import SourceDescriptor


def test_top_level_relation_is_normalized():
    result = AdapterResult(items=[{"id":"r1","subject_ref":"urn:a","predicate":"related_to","object_ref":"urn:b"}])
    batch = normalize_result("Mock", "rel", result, SourceDescriptor(state_id="sha256:x"))
    assert len(batch.records) == 1
    assert len(batch.relations) == 1
    assert batch.relations[0].subject_ref == "urn:a"
    assert batch.relations[0].object_ref == "urn:b"
    assert {x.referent_id for x in batch.referents} == {"urn:a", "urn:b"}
