"""Optional sealed export of two final-only evaluation JSONs; no provider calls."""
import argparse, io, base64, gzip, hashlib, importlib, json, os, re, sys, tempfile
from pathlib import Path

RUN = 41964609630
NONCE = "53d976909bcb8156d466bb8d4cb923cd"
COMMIT = "a00c8f99da516361a5210fab328efe5fe911bfce"
PROOF_SHA = '6c0ab2d2dc6748189b02cb2ef00a53c1d84def79a1dd1097fbf843c925225dd0'
MANIFEST_SHA = '83aa633cd60df8eb572c88a739aca7ea7bff5ddaf72781f27cd1e1812c49b311'
RESULT_PREFIX = 'private_qwq_gpu_result_json'
FINAL_FILES = [{'name':'report.json','bytes':4787,'sha256':'4e013762afe3488c38d75293df93772b4c33ac364ce0042fe4ba43d8be5d29f1'},
               {'name':'metadata.json','bytes':2354,'sha256':'52c4ab265f1b701820ab4798dfc304549939d896590d467199058aa6019c5d2f'}]
MAX_RAW = 2 * 1024**2
CHUNK = 32000
PINS = {
 "private_qwq_gpu_eval.py": "34c09c2a2db22f9b4c525030736e61039b6c2d72ddcc2d55d9bb888e635de0af",
 "private_qwq_comparison.py": "280bfeef08d8bd9d26feddc784cf4724687373ae4c186302bc0d171b103298db",
 "private_resume_adapter.py": "e52f9e5c31d938c98b7f3215761e3a3ccee616c645b74bd4cfa899cb34b551af",
 "private_verify_adapter.py": "e349889bbbd25fc5aa80ff32f43c2a3911a3f21ca0fd6f8b530d9b82142063a9",
 "role_config.py": "fde4850efcb0002d3458772956fcf61398c705814e1d6534981404ae495eac03"}

class ExportError(ValueError): pass
def require(value, code):
    if not value: raise ExportError(code)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()

def load_code(directory):
    directory = Path(directory).resolve()
    for name, pin in PINS.items():
        path = directory / name
        require(path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == pin, "code_pin_mismatch")
        loaded = sys.modules.get(Path(name).stem)
        require(loaded is None or Path(loaded.__file__).resolve() == path, "mixed_code_cache")
    sys.path.insert(0, str(directory))
    return importlib.import_module("private_qwq_gpu_eval"), importlib.import_module("private_resume_adapter")

def bound_terminal(raw, expected_sha, worker, resume):
    require(expected_sha == PROOF_SHA and sha(raw) == PROOF_SHA and 0 < len(raw) <= 4*1024**2, 'terminal_proof_pin_mismatch')
    proof=resume._json(raw)
    require(type(proof) is dict and type(proof.get('id')) is int and proof['id']==RUN and proof.get('head_sha')==COMMIT
            and proof.get('status')=='completed' and proof.get('conclusion')=='failure','terminal_run_unbound')
    events=proof.get('events');require(type(events) is list and all(type(e) is dict for e in events),'terminal_events_invalid')
    def one(name):
        rows=[e for e in events if e.get('event')==name];require(len(rows)==1,'single_terminal_event_required');return rows[0]
    pre=one('private_qwq_gpu_preflight');start=one('private_qwq_gpu_started');cost=one('private_qwq_gpu_cost')
    require(pre.get('run_id')==str(RUN) and pre.get('code_commit')==COMMIT and pre.get('launch_id')==NONCE
            and pre.get('manifest_sha256')==MANIFEST_SHA and start.get('run_id')==str(RUN)
            and start.get('pod_name')=='hasla-private-qwq-eval-'+str(RUN) and type(start.get('pod_id')) is str,
            'terminal_source_or_pod_unbound')
    clean=[e for e in events if e.get('event')=='private_qwq_gpu_cleanup']
    require(len(clean)==2 and all(e.get('attempted') is True and e.get('deletion_confirmed') is True for e in clean)
            and [e.get('matched_pods') for e in clean]==[1,0] and cost.get('run_id')==str(RUN)
            and type(cost.get('run_upper_krw')) is int and cost['run_upper_krw']==578
            and cost.get('aggregate_upper_krw')==73916 and cost.get('deletion_confirmed') is True,'terminal_cleanup_or_cost_unverified')
    require(not any(e.get('event')=='private_qwq_gpu_evaluation' for e in events),'parent_receipt_present_use_original_exporter')
    return {'terminal_proof_sha256':PROOF_SHA,'parent_evaluation_receipt_present':False,'known_pod_deletion_confirmed':True}


def real_summary_result(api, worker, resume):
    name='hasla-qwq-gpu-comparison-'+str(RUN)
    with resume._quiet():
        run=api.run(worker.ENTITY+'/'+resume.PROJECT+'/'+name)
        require(run.id==name and run.entity==worker.ENTITY and run.project==resume.PROJECT,'summary_run_identity_mismatch')
        summary=run.summary._json_dict
    require(type(summary) is dict and len(canonical(summary))<=1024**2,'summary_bound')
    value=summary.get(RESULT_PREFIX)
    if type(value) is str:value=resume._json(value)
    flat={k[len(RESULT_PREFIX)+1:]:v for k,v in summary.items() if k.startswith(RESULT_PREFIX+'.')}
    if flat:
        require(len(flat)<=128 and not any(b.startswith(a+'.') for a in flat for b in flat if a!=b),'summary_flat_collision')
        from copy import deepcopy
        reconstructed={}
        for path,item in flat.items():
            parts=path.split('.');require(len(parts)<=5 and all(re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,79}',p) for p in parts),'summary_flat_path')
            node=reconstructed
            for part in parts[:-1]:
                if part not in node:node[part]={}
                require(type(node[part]) is dict,'summary_flat_collision');node=node[part]
            require(parts[-1] not in node,'summary_flat_collision');node[parts[-1]]=deepcopy(item)
        require(value is None or canonical(value)==canonical(reconstructed),'summary_alias_collision')
        value=reconstructed
    result=worker.validate_result(value,str(RUN));require(result['status']=='uploaded'
        and result['artifact']==worker.ENTITY+'/'+resume.PROJECT+'/hasla-qwq-gpu-comparison-'+str(RUN)+':v0'
        and result['files']==FINAL_FILES and result['execution_status']=='completed' and result['paired_completed_cases']==8,
        'uploaded_summary_result_required')
    return result


def recipient_box(public_key):
    from nacl.public import PublicKey, SealedBox
    try:
        public = base64.b64decode(public_key, validate=True)
        require(type(public_key) is str and len(public) == 32
                and base64.b64encode(public).decode() == public_key, "public_key_not_canonical")
        box = SealedBox(PublicKey(public)); box.encrypt(b"recipient-validation")
    except Exception: raise ExportError("public_key_invalid") from None
    return public, box

def export_events(proof_raw, proof_sha, public_key, api, privacy, worker, resume):
    public, box = recipient_box(public_key)
    terminal = bound_terminal(proof_raw, proof_sha, worker, resume)
    resume._private(privacy, worker.ENTITY)
    result = real_summary_result(api, worker, resume)
    resume._private(privacy, worker.ENTITY)
    expected_meta = {"private": True, "evaluation_only": True, "optimizer_steps": 0, "run_id": str(RUN),
        "code_commit": COMMIT, "case_set_sha256": worker.CASE_SHA,
        "source_adapter_inventory_sha256": worker.SOURCE["adapter_inventory_sha256"], "files": result["files"]}
    with resume._quiet():
        artifact = api.artifact(result["artifact"], type="evaluation")
        require(artifact.qualified_name == result["artifact"] and artifact.state == "COMMITTED"
                and artifact.type == "evaluation" and not getattr(artifact, "is_link", False)
                and artifact.metadata == expected_meta, "artifact_identity_mismatch")
        creator=artifact.logged_by()
        require(creator is not None and creator.id=='hasla-qwq-gpu-comparison-'+str(RUN)
                and creator.entity==worker.ENTITY and creator.project==resume.PROJECT,'artifact_creator_unbound')
        entries = artifact.manifest.entries
        require(type(entries) is dict and set(entries) == {"report.json", "metadata.json"}, "artifact_entries_mismatch")
    with tempfile.TemporaryDirectory(prefix="hasla-sealed-eval-") as temporary:
        root = Path(temporary); files = []
        for row in result["files"]:
            resume._entry(entries[row["name"]], row)
            resume._private(privacy, worker.ENTITY)
            with resume._quiet():
                entry = artifact.get_entry(row["name"]); resume._entry(entry, row)
                path = Path(entry.download(root=str(root), skip_cache=True))
            require(path.absolute() == (root / row["name"]).absolute() and path.is_file()
                    and not path.is_symlink() and path.resolve() == (root / row["name"]).resolve()
                    and path.stat().st_size == row["bytes"], "downloaded_file_invalid")
            raw = path.read_bytes(); require(sha(raw) == row["sha256"], "downloaded_file_hash_mismatch")
            files.append({**row, "base64": base64.b64encode(raw).decode()})
        worker.validate_outputs(root)
        metadata = resume._json((root / "metadata.json").read_bytes())
        require(metadata["run_id"] == str(RUN) and metadata["code_commit"] == COMMIT, "artifact_execution_mismatch")
        require(set(path.name for path in root.iterdir()) == {"report.json", "metadata.json"}, "extra_download_files")
    resume._private(privacy, worker.ENTITY)
    raw = canonical({"version": 1, "kind": "private_qwq_final_artifact_discovery_export", "run_id": str(RUN),
        "code_commit": COMMIT, "artifact": result["artifact"], "observed_worker_summary_result": result, "terminal_binding": terminal, "parent_receipt_fabricated": False, "files": files})
    require(len(raw) <= MAX_RAW, "export_plaintext_bound")
    compressed = gzip.compress(raw, mtime=0)
    cipher = box.encrypt(compressed); encoded = base64.b64encode(cipher).decode()
    parts = (len(encoded) + CHUNK - 1) // CHUNK
    metadata = {"version": 1, "algorithm": "libsodium_sealed_box_curve25519xsalsa20poly1305", "compression": "gzip",
        "run_id": str(RUN), "code_commit": COMMIT, "proof_sha256": proof_sha, "result_sha256": sha(canonical(result)),
        "artifact": result["artifact"], "files": result["files"], "parent_evaluation_receipt_present": False, "result_origin": "actual_private_worker_summary_and_committed_artifact", "public_key_sha256": sha(public),
        "raw_sha256": sha(raw), "raw_bytes": len(raw), "gzip_bytes": len(compressed), "cipher_bytes": len(cipher),
        "cipher_sha256": sha(cipher), "base64_characters": len(encoded), "parts": parts}
    events = [{"event": "private_qwq_gpu_observation", "artifact_export_fragment": {"part": i, "parts": parts,
        "cipher_sha256": sha(cipher), "base64": encoded[i * CHUNK:(i + 1) * CHUNK]}} for i in range(parts)]
    events.append({"event": "private_qwq_gpu_observation", "artifact_export": metadata})
    require(all(len(canonical(event)) < 48 * 1024 for event in events), "export_event_bound")
    return events

def main():
    try:
        worker,resume=load_code(Path(__file__).parent)
        encoded=os.environ.get('HASLA_QWQ_FINAL_DISCOVERY_PROOF_GZ_B64','')
        require(type(encoded) is str and 0<len(encoded)<=32768,'proof_envelope_invalid')
        compressed=base64.b64decode(encoded,validate=True);chunks=[];total=0
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            while True:
                chunk=stream.read(65536)
                if not chunk:break
                total+=len(chunk);require(total<=4*1024**2,'proof_decompression_bound');chunks.append(chunk)
        raw=b''.join(chunks);bound_terminal(raw,PROOF_SHA,worker,resume)
        public=os.environ.get('HASLA_EVAL_EXPORT_PUBLIC_KEY','');recipient_box(public)
        api,privacy,_=worker.private_clients(os.environ)
        for event in export_events(raw,PROOF_SHA,public,api,privacy,worker,resume):
            print(canonical(event).decode(),flush=True)
        return 0
    except Exception:
        print('{"event":"private_qwq_gpu_observation_failed","failure_code":"private_final_discovery_failed"}')
        return 1
if __name__=='__main__':raise SystemExit(main())
