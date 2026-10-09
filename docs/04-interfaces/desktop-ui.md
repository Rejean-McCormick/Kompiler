# Desktop UI

## Product goal

Provide a frictionless local bridge between an LLM conversation and heavy Kristal queries without making the GUI part of the protocol.

## Primary screens

### Capability Inventory

- installed targets;
- adapter health;
- Kristal source identity/version;
- operations and limits;
- copy/export capability snapshot.

### Query Inbox

- paste JSON;
- drag/drop `.json`;
- syntax/schema diagnostics;
- DAG visualization;
- estimated operation count and declared budgets;
- explicit Run action.

### Run Monitor

- stages and node statuses;
- elapsed times;
- item counts;
- truncation/errors;
- cancel button.

### Context Pack Viewer

- summary counts;
- target/source facets;
- records/relations;
- conflicts/gaps;
- provenance inspector;
- copy/export whole pack;
- optional compact LLM transfer representation.

## Security UX

The UI MUST clearly distinguish:

- untrusted Query Plan content;
- trusted adapter mappings;
- read-only operations;
- source integrity failures;
- partial/truncated results.

The UI MUST NOT render a query's arbitrary text as executable shell instructions.

## Future convenience

A browser extension, custom ChatGPT integration, or MCP client can replace copy/paste later. The desktop UI remains useful for inspection, auditing, and large-run control.


## Reference implementation

The repository ships a React + Vite frontend and a Tauri v2 shell. The UI talks to the local FastAPI transport. Browser/webview origins are not implicitly trusted: when HTTP transport is used, the operator explicitly configures `api.cors_origins`. Query semantics remain exclusively in the Python runtime.
