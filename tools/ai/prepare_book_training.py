"""Prepare user-requested, private textbook language-model data from an immutable inventory.

This records the operator's instruction, not a claim of copyright ownership or a
third-party license grant. Approval here covers native-text extraction quality;
it does not assert that a page is a verified solution or a conversational answer.
"""
import argparse
import hashlib
import json
from pathlib import Path

from corpus_prepare import prepare_corpus, write_corpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--dataset-version', required=True)
    parser.add_argument('--authorization-note', required=True)
    args = parser.parse_args()
    root = args.inventory_dir.resolve()
    inventory = json.loads((root / 'inventory.json').read_text(encoding='utf-8'))
    payload = root / 'pages.jsonl'
    with payload.open('rb') as handle:
        if hashlib.file_digest(handle, 'sha256').hexdigest() != inventory['payload']['sha256']:
            parser.error('inventory payload checksum mismatch')
    sources = json.loads((root / 'sources.json').read_text(encoding='utf-8'))
    source_map = {}
    for row in sources:
        source_map[row['id']] = {**row, 'rights_status': 'user_provided', 'allowed_uses': ['train'],
            'permission_reference': args.authorization_note, 'authorization_scope': 'private_requested_training',
            'copyright_ownership_asserted': False, 'third_party_license_grant_inferred': False}
    rows, empty_pages = [], 0
    with payload.open(encoding='utf-8') as handle:
        for line in handle:
            row = json.loads(line)
            if not row['text'].strip():
                empty_pages += 1
                continue
            meta = row['metadata']
            if meta['quality_gate']['status'] != 'ready_for_review':
                row['review_status'] = 'excluded'
                meta['exclusion_reason'] = 'native_text_quality_gate'
            else:
                row['review_status'] = 'approved'
                meta.update({'review_scope': 'native_text_extraction_only', 'human_scientific_review': False,
                             'training_eligible': True, 'training_authorization': args.authorization_note})
            rows.append(row)
    prepared = prepare_corpus(rows, source_map, args.dataset_version)
    prepared['manifest']['empty_native_text_pages_in_raw_inventory'] = empty_pages
    result = write_corpus(prepared, args.output_dir)
    print(json.dumps({k: result[k] for k in ('records', 'groups', 'exports', 'exclusions')}, ensure_ascii=True))


if __name__ == '__main__':
    main()
