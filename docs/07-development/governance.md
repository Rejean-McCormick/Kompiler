# Governance and Ownership

## Project ownership

The repository SHOULD define the following roles before public/multi-maintainer release:

- **Protocol owner** — approves wire/semantic contract changes.
- **Runtime owner** — owns planner/executor/compiler implementation.
- **Security owner** — reviews adapter execution, filesystem, network, and permission changes.
- **Adapter owner(s)** — one or more maintainers per Kristal adapter.
- **Release owner** — signs/releases artifacts and coordinates compatibility gates.

Names and contact addresses are intentionally not invented in this documentation. Add them to `CODEOWNERS`, repository metadata, and the security policy when known.

## Decision process

Cross-cutting architectural changes require an ADR. Protocol-breaking changes require:

1. ADR;
2. migration plan;
3. new conformance vectors;
4. major protocol/version change where applicable.

## Security reporting

Before external release, add a root `SECURITY.md` with a private reporting channel. Do not ask reporters to disclose vulnerabilities through public issues.

## Compatibility promise

Adapters may evolve independently, but a published capability snapshot is treated as an immutable description of what a particular run environment advertised at that moment.
