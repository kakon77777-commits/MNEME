from pathlib import Path
import pytest

from mneme.dry_run.bundle import bundle_manifest, bundle_fingerprint, verify_bundle, write_evidence_bundle
from mneme.errors import DryRunValidationError


def test_bundle_manifest_is_sorted_and_tamper_detected():
    files={'z.txt':b'z\n','a.json':b'{}\n'}
    manifest=bundle_manifest(files)
    assert [x['path'] for x in manifest['files']]==['a.json','z.txt']
    fp=bundle_fingerprint(manifest)
    assert verify_bundle(files,manifest) is True
    tampered=dict(files); tampered['a.json']=b'{"x":1}\n'
    assert verify_bundle(tampered,manifest) is False
    assert bundle_fingerprint(bundle_manifest(tampered)) != fp


def test_writer_refuses_source_destination_and_different_existing_bytes(tmp_path):
    source=tmp_path/'MEMORY.md'; source.write_text('private',encoding='utf-8')
    with pytest.raises(DryRunValidationError):
        write_evidence_bundle({'report.json':b'{}\n'}, source, source_path=source)
    out=tmp_path/'report'; out.mkdir(); (out/'report.json').write_bytes(b'old')
    with pytest.raises(DryRunValidationError):
        write_evidence_bundle({'report.json':b'new'}, out, source_path=source)
    assert source.read_text()=='private'


def test_writer_rejects_evidence_payload_equal_to_source_bytes(tmp_path):
    source = tmp_path / "MEMORY.md"
    source.write_bytes(b"private source bytes\n")
    with pytest.raises(DryRunValidationError):
        write_evidence_bundle(
            {"pass1/source-copy.md": source.read_bytes()},
            tmp_path / "report",
            source_path=source,
        )
