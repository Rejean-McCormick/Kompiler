# Capabilities Contract

`kompiler.capabilities/1.1` tells an LLM or client exactly what the current runtime can do.

## Required shape

```json
{
  "protocol": "kompiler.capabilities",
  "version": "1.1",
  "snapshot_id": "cap:sha256:...",
  "generated_at": "2026-10-02T15:00:00Z",
  "runtime": {
    "name": "kompiler",
    "version": "1.0.0"
  },
  "targets": []
}
```

## Target descriptor

```json
{
  "target_id": "HumanBody",
  "kind": "kristal",
  "adapter": {
    "id": "kristal-humanbody",
    "version": "1.0.0"
  },
  "source": {
    "kristal_schema_version": "6.0",
    "state_id": "sha256:..."
  },
  "operations": []
}
```

## Operation descriptor

```json
{
  "operation_id": "mechanisms",
  "description": "Retrieve mechanism-oriented assertions relevant to a topic.",
  "input_schema": {
    "type": "object",
    "properties": {
      "topic": {"type": "string"},
      "limit": {"type": "integer", "minimum": 1, "maximum": 500}
    },
    "required": ["topic"],
    "additionalProperties": false
  },
  "output": {
    "record_kinds": ["assertion", "relation"],
    "supports_provenance": true
  },
  "semantics": {
    "read_only": true,
    "deterministic": true,
    "supports_reader_policy": true
  },
  "limits": {
    "max_items": 500,
    "timeout_ms": 30000
  }
}
```

## Capability dimensions

An operation SHOULD advertise support for applicable dimensions instead of implying universal support:

- referent/subject/predicate/object;
- assertion status;
- valuations and value semantics;
- coordinates/applicability;
- record role;
- actionability;
- evidence/source;
- validation/recognition;
- conflict/supersession/lineage;
- pagination;
- cardinality;
- joins;
- domain-specific projections.

## Capability snapshot binding

A Query Plan SHOULD include `capability_snapshot_id`. If the current runtime snapshot differs, default behavior is `CAPABILITY_SNAPSHOT_MISMATCH`. A caller MAY explicitly allow compatible drift, but never silent semantic drift.

## Agent guidance

Descriptions are part of the LLM-facing interface. They SHOULD explain intent, not implementation. Do not expose shell templates as capability descriptions.

## Protocol 1.1: semantic-plane declarations

Operation semantics may advertise:

```json
{
  "semantic_plane": "meta",
  "requires_surface": true,
  "v7_native": true
}
```

`semantic_plane=source` remains the default for traditional Kristal adapters. A v7-native Surface operation uses `meta` and may require a Surface selector.

The runtime descriptor also advertises standard support, currently including v6 source/projection states and Kristall v7 draft.3.2 meta-artifacts.

## v7 conformance advertisement

Protocol 1.1 runtime descriptors include `conformance_profiles`. Kompiler 0.5 advertises:

```json
{
  "conformance_profiles": {
    "kristal_v7": "V7-Projection"
  }
}
```

This is deliberately lower than `V7-Kristall`: the runtime can read source states, consume Mesh structure, compile Surfaces and materialize portable projections, but does not claim the full crystallization/promotion/reconstruction lifecycle.
