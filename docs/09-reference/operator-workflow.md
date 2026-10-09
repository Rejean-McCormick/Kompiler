# Operator Workflow

## Clipboard-first

1. Run `kompiler capabilities --json`.
2. Give the capability snapshot to the LLM.
3. Ask the LLM to return one `kompiler.query/1.1` JSON artifact.
4. Paste/drop that JSON into the desktop Query Inbox or run it through the CLI.
5. Execute locally.
6. Copy the resulting Context Pack into the conversation.
7. Continue reasoning; issue follow-up Query Plans only where the Context Pack exposes gaps.

## Desktop

Run the Python API and the desktop frontend. The UI is intentionally a control/inspection surface; query semantics live only in the Python core.

Local browser/webview origins must be explicitly listed under `api.cors_origins` when the UI uses HTTP transport.

## Heavy sessions

For large plans, use async API runs so the UI can display receipts and cancellation state. Context Packs remain normal protocol artifacts regardless of transport.
