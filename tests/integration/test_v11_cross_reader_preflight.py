"""Pinned Framework→Pack→Kompiler/EncyKlopedia private consumer campaign.

Not run automatically without all three external checkouts; never a public
publication test. Uses exact input bytes and an independent Node consumer.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from kompiler.adapters.base import AdapterContext
from kompiler.adapters.kristal_v11 import KristalV11ReadViewAdapter
from kompiler.adapters.manifest import AdapterManifest

FW = os.getenv('KOMPILER_V11_FRAMEWORK_ROOT')
PACK = os.getenv('KOMPILER_V11_PACK_ROOT')
ENCY = os.getenv('KOMPILER_V11_ENCYKLOPEDIA_ROOT')
pytestmark = pytest.mark.skipif(not all((FW, PACK, ENCY)), reason='requires exact offline Framework, Pack and EncyKlopedia sources')


def test_three_owner_private_v11_read_receipts(tmp_path):
    framework = Path(FW).resolve()
    pack = Path(PACK).resolve()
    ency = Path(ENCY).resolve()
    root = framework / 'examples/v11'
    files = {'graph': root / 'semantic-graph.example.json',
             'registry': root / 'identity-registry.example.json',
             'crosswalk': root / 'external-crosswalk.example.json',
             'catalog': root / 'dictionaries/catalog.json'}
    output = tmp_path / 'view.json'
    cmd = [sys.executable, str(pack / 'tools/v11_integration.py'), 'view', '--framework', str(framework)]
    for key, path in files.items():
        cmd += ['--' + key, str(path)]
    cmd += ['--locale', 'fr-CA', '--out', str(output)]
    result = subprocess.run(cmd, cwd=pack, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    view = json.loads(output.read_text())

    manifest = AdapterManifest(id='v11', version='0.1.0', target_id='KristalV11:demo', kind='kristal', root=root,
        adapter_type='kristal-v11-read-view', options={
          'local_read_approved': True, 'framework_root': str(framework), 'integration_pack_root': str(pack),
          'registry': 'identity-registry.example.json', 'graph': 'semantic-graph.example.json',
          'crosswalk': 'external-crosswalk.example.json', 'catalog': 'dictionaries/catalog.json'})
    adapter = KristalV11ReadViewAdapter(manifest)
    read = asyncio.run(adapter.execute('read', {'locale':'fr-CA','semantic_ids':['KQ1001','KP2001','KA3001','KS4001']},
        AdapterContext(operation_id='read', timeout_ms=30000)))
    assert read.metadata['publication_authorized'] is False
    assert read.metadata['coverage_counts'] == view['coverage_counts']
    assert read.metadata['canonical_source_digests'] == {name+'_sha256':hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}

    ency_cmd = ['node',str(ency/'tools/private-v11-preflight.mjs'), '--view',str(output)]
    for key,path in files.items():
        ency_cmd += ['--'+key,str(path)]
    private = subprocess.run(ency_cmd, capture_output=True,text=True,timeout=15)
    assert private.returncode == 0, private.stderr
    receipt = json.loads(private.stdout)
    assert receipt['status']=='STRUCTURALLY_VERIFIED_NOT_PUBLIC'
    assert receipt['input_view_sha256']==hashlib.sha256(output.read_bytes()).hexdigest()
    assert receipt['counts']['lexical']==view['coverage_counts']
    assert receipt['publication_authorized'] is False
    assert receipt['framework_validation_performed'] is False

    view['presentation'][0]['semantic_id'] = 'Q1'  # no externally named ID can replace a KQ/KP
    rejected = tmp_path/'tampered.json'
    rejected.write_text(json.dumps(view),encoding='utf8')
    cmd = ency_cmd.copy();cmd[cmd.index('--view')+1]=str(rejected)
    bad = subprocess.run(cmd,capture_output=True,text=True,timeout=15)
    assert bad.returncode != 0
    assert 'PRIVATE_V11_REJECTED' in bad.stderr
