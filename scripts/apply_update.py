#!/usr/bin/env python3
"""Apply a narrow, guarded read-only v10 alignment update to Kompiler.

The script does not contact GitHub, modify Kristal states, or run publication.
Pass the path to a local checkout (one with src/kompiler/github_collection.py).
All original files are checked for expected source anchors before ANY writes.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
import sys

MARKER = '# v10 reader provenance: schema-compatible metadata additions'

REPLACEMENTS: dict[str, list[tuple[str, str]]] = {
    'src/kompiler/github_collection.py': [
        (
            'return {"repository": self.source_uri, "count": len(rows), "entries": rows[max(0, offset):max(0, offset) + min(200, max(1, limit))], "index_digest": self.index["index_digest"]}',
            'return {"repository": self.source_uri, "source_revision": self.revision, "count": len(rows), "entries": rows[max(0, offset):max(0, offset) + min(200, max(1, limit))], "index_digest": self.index["index_digest"]}',
        ),
        (
            '"surface_digest": manifest["surface_digest"], "source": self.source_uri}',
            '"surface_digest": manifest["surface_digest"], "state_logical_commitment": manifest["state_logical_commitment"], "source_revision": self.revision, "source": self.source_uri}',
        ),
        (
            '"surface_digest": m["surface_digest"], "entrypoint": f"kristals/{slug}/AI_START_HERE.md", "files": m["files"][:min(500, max(1, limit))], "file_count": m["file_count"], "materialization_object_count": m["materialization_object_count"], "source": self.source_uri}',
            '"surface_digest": m["surface_digest"], "state_logical_commitment": m["state_logical_commitment"], "source_revision": self.revision, "entrypoint": f"kristals/{slug}/AI_START_HERE.md", "files": m["files"][:min(500, max(1, limit))], "file_count": m["file_count"], "materialization_object_count": m["materialization_object_count"], "source": self.source_uri}',
        ),
    ],
    'src/kompiler/adapters/github_collection.py': [
        (
            '"index_digest": self.reader.index["index_digest"], "network": self.reader.is_network}',
            '"index_digest": self.reader.index["index_digest"], "source_revision": self.reader.revision, "network": self.reader.is_network}',
        ),
    ],
    'README.md': [
        (
            '**Kristal alignment:** exact contract-set pins for `10.0.0-draft.2` and the supplied `10.0.0-draft.3` snapshot; an explicit operator SHA-256 is still accepted for another draft.3 checkout',
            '**Kristal alignment:** exact contract-set pins for `10.0.0-draft.2`, `10.0.0-draft.3`, and `10.0.0-draft.3.1`. Unrecognized contract sets require a separately verified operator SHA-256; Framework status remains draft.',
        ),
    ],
    'docs/03-runtime/github-collection-reader.md': [
        (
            'It does not claim that those checks alone prove all referenced physical materializations are available; large blobs remain separate host-transport objects.',
            'It does not claim that those checks alone prove all referenced physical materializations are available; large blobs remain separate host-transport objects. Every selected file result and file-map response carries its declared `state_logical_commitment`, and remote results also carry `source_revision` (the full pinned Git commit SHA). A local checkout has `source_revision: null`: there is no invented Git identity. These identifiers describe the read surface, not independent qualification.',
        ),
    ],
}

ADDITIONS = {
    'tests/integration/test_v10_provenance_metadata.py': 'tests/test_v10_provenance_metadata.py',
    'docs/03-runtime/v10-alignment-update.md': 'docs/v10-alignment-update.md',
}


def stage(root: Path, bundle: Path) -> tuple[dict[Path, bytes], dict[Path, bytes]]:
    changes: dict[Path, bytes] = {}
    originals: dict[Path, bytes] = {}
    for rel, changeset in REPLACEMENTS.items():
        path = root / rel
        if not path.is_file():
            raise ValueError(f'Missing expected repository file: {rel}')
        original = path.read_bytes()
        text = original.decode('utf-8')
        updated = text
        for old, new in changeset:
            if old == new:
                raise ValueError(f'No-op replacement in {rel}')
            count = updated.count(old)
            if count != 1:
                raise ValueError(f'Unexpected source for {rel}: anchor has {count} matches, expected exactly one. No changes applied.')
            updated = updated.replace(old, new, 1)
        if updated == text:
            raise ValueError(f'No changes prepared for {rel}')
        changes[path] = updated.encode('utf-8')
        originals[path] = original
    for rel, source in ADDITIONS.items():
        path = root / rel
        if path.exists():
            raise ValueError(f'Refusing to replace an existing file: {rel}')
        changes[path] = (bundle / source).read_bytes()
    return changes, originals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path, help='Local Kompiler repository checkout')
    parser.add_argument('--apply', action='store_true', help='Write changes (default is a read-only preview)')
    parser.add_argument('--backup-dir', type=Path, help='Optional backup directory for original files')
    args = parser.parse_args()
    root = args.repo.expanduser().resolve()
    bundle = Path(__file__).resolve().parents[1]
    if not (root / 'pyproject.toml').is_file():
        parser.error('Kompiler pyproject.toml was not found at repository root')
    try:
        changes, originals = stage(root, bundle)
    except (ValueError, OSError, UnicodeError) as exc:
        print(f'BLOCKED: {exc}', file=sys.stderr)
        return 2
    print(f'Guarded update ready: {len(changes)} files')
    for path, content in changes.items():
        print('  ' + ('MODIFY' if path in originals else 'CREATE') + ' ' + str(path.relative_to(root))
              + f'  sha256={hashlib.sha256(content).hexdigest()}')
    if not args.apply:
        print('PREVIEW ONLY: no files written. Re-run with --apply and preferably --backup-dir.')
        return 0
    if args.backup_dir:
        backup = args.backup_dir.expanduser().resolve()
        for path, old in originals.items():
            dest = backup / path.relative_to(root)
            if dest.exists():
                print(f'BLOCKED: refusing to overwrite backup {dest}', file=sys.stderr)
                return 2
        for path, old in originals.items():
            dest = backup / path.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(old)
    created: list[Path] = []
    try:
        for path, content in changes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            if path not in originals:
                created.append(path)
    except OSError as exc:
        for path, data in originals.items():
            path.write_bytes(data)
        for path in created:
            path.unlink(missing_ok=True)
        print(f'Rolled back due to write error: {exc}', file=sys.stderr)
        return 2
    print('Applied locally. Next: run project test suite, review git diff, and open a PR manually.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
