# Security Policy

Kompiler treats LLM-produced Query Plans as untrusted input. Report security issues through the repository's private security advisory mechanism when available; do not include sensitive local Kristal data in public issues.

High-priority classes include command injection, path traversal/symlink escape, arbitrary executable discovery, secret leakage, network-policy bypass, provenance stripping, capability spoofing, and resource-limit bypass.

The v1 query protocol is read-only by design. `actionability` values contained in Kristal data are knowledge, not Kompiler permissions.
