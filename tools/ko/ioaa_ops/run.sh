#!/bin/bash
# Rebuild one IOAA Korean solution from its source copy with the ops in this folder:
#   pre ops (overlay_retext.py) -> table rows (overlay_table.py) -> post ops (overlay_retext.py)
#   -> sentences set around the original's math (place_pieces.py, needs the English original)
# usage: tools/ko/ioaa_ops/run.sh <src.pdf> <out.pdf> [<english original.pdf>]
#        (name taken from the file name, e.g. IOAA_2025_G1_S_KO)
set -e
T=$(cd "$(dirname "$0")/.." && pwd)
OPS=$T/ioaa_ops
src=$1; out=$2; orig=$3; n=$(basename "$src" .pdf)
tmp=$(mktemp -d)
if [ -f "$OPS/$n.pre.json" ]; then python3 "$T/overlay_retext.py" "$src" "$tmp/1.pdf" "$OPS/$n.pre.json"; else cp "$src" "$tmp/1.pdf"; fi
python3 "$T/overlay_table.py" "$tmp/1.pdf" "$tmp/2.pdf" | grep -v rebuilt || true
if [ -f "$OPS/$n.post.json" ]; then python3 "$T/overlay_retext.py" "$tmp/2.pdf" "$tmp/3.pdf" "$OPS/$n.post.json"; else cp "$tmp/2.pdf" "$tmp/3.pdf"; fi
if [ -f "$OPS/$n.pieces.json" ]; then
  [ -n "$orig" ] || { echo "$n needs the English original as third argument" >&2; exit 1; }
  python3 "$T/place_pieces.py" "$tmp/3.pdf" "$orig" "$out" "$OPS/$n.pieces.json"
else cp "$tmp/3.pdf" "$out"; fi
rm -rf "$tmp"
