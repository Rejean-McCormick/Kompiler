# Kristal v9 read surface

Kompiler is a `V9-State-Reader`, not a publisher. The v9 adapter reads immutable State Snapshots and local Logical Artifacts from `.kristal/v9/`, validates them against the externally configured Kristal Standard, and exposes them as source records to the context compiler.

It never mints semantic IDs, recalculates a replacement authoritative commitment, follows mutable `latest` selectors, activates a state, or treats Runtime/Materialization metadata as canon.
