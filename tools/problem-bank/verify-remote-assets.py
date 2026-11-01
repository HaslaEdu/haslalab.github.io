"""Read back private D1 sample crops and verify their stored bytes and image type.

Uses an already authenticated Wrangler CLI. Does not read credentials, enable
services, call model APIs, write source bytes, or mark content reviewed.
"""
import argparse
import hashlib
import io
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from private_paths import private_directory


def verify(database, config, wrangler, output, per_source):
    if not 1 <= per_source <= 5:
        raise ValueError('Sample size must be between one and five per source')
    output = private_directory(output.parent) / output.name
    # Largest assets exercise multi-chunk reconstruction as well as image decode.
    sql = f"""WITH ranked AS (
      SELECT a.id,a.sha256,a.mime_type,p.byte_length,p.chunk_count,q.source_id,
        ROW_NUMBER() OVER(PARTITION BY q.source_id ORDER BY p.byte_length DESC,a.id) AS n
      FROM bank_assets a JOIN bank_questions q ON q.id=a.question_id
      JOIN bank_asset_payloads p ON p.asset_id=a.id)
      SELECT r.*,c.chunk_index,c.byte_length AS chunk_length,c.sha256 AS chunk_sha256,
        hex(c.payload) AS payload_hex FROM ranked r
      JOIN bank_asset_chunks c ON c.asset_id=r.id WHERE r.n<={per_source}
      ORDER BY r.source_id,r.id,c.chunk_index;"""
    result = subprocess.run(['node', str(wrangler.resolve()), 'd1', 'execute', database,
                             '--remote', '--config', str(config.resolve()),
                             '--command', sql, '--json'],
                            capture_output=True, text=True, encoding='utf-8', check=True)
    response = json.loads(result.stdout)
    if not response or any(not item.get('success') for item in response):
        raise ValueError('Remote readback did not succeed')
    groups = {}
    for item in response:
        for row in item['results']:
            groups.setdefault(row['id'], []).append(row)
    if not groups:
        raise ValueError('No inline crops were read back')
    assets, byte_count, sources, multi_chunk = 0, 0, set(), 0
    for asset_id, rows in groups.items():
        first, chunks = rows[0], []
        if [row['chunk_index'] for row in rows] != list(range(first['chunk_count'])):
            raise ValueError(f'Nonconsecutive chunks: {asset_id}')
        for row in rows:
            data = bytes.fromhex(row['payload_hex'])
            if len(data) != row['chunk_length'] or hashlib.sha256(data).hexdigest() != row['chunk_sha256']:
                raise ValueError(f'Corrupt chunk: {asset_id}')
            chunks.append(data)
        image_bytes = b''.join(chunks)
        if len(image_bytes) != first['byte_length'] or hashlib.sha256(image_bytes).hexdigest() != first['sha256']:
            raise ValueError(f'Corrupt assembled image: {asset_id}')
        with Image.open(io.BytesIO(image_bytes)) as picture:
            if Image.MIME[picture.format] != first['mime_type']:
                raise ValueError(f'Unexpected image format: {asset_id}')
            picture.verify()
        assets += 1
        byte_count += len(image_bytes)
        sources.add(first['source_id'])
        multi_chunk += first['chunk_count'] > 1
    report = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'server_readback': True, 'sampling': 'largest assets per source',
              'sample_per_source': per_source, 'sampled_sources': len(sources),
              'sampled_assets': assets, 'multi_chunk_assets': multi_chunk,
              'verified_bytes': byte_count, 'hash_mismatches': 0,
              'image_decode_failures': 0, 'content_review_status': 'pending',
              'paid_model_api_calls': 0}
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--wrangler', type=Path, default=Path('community/node_modules/wrangler/bin/wrangler.js'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sample-per-source', type=int, default=2)
    args = parser.parse_args()
    verify(args.database, args.config, args.wrangler, args.out, args.sample_per_source)
