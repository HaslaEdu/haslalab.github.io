"""Pack scanic-ml's DocCornerNet LEAN model (doccornernet_lean.ort) for the web.

The browser still runs the original fp32 model on the same custom ONNX Runtime build, so inference speed is
unchanged. Only the download is smaller: the 48 large weight tensors (>= 1024 values, 96% of the weights) are
stored as fp16, high bytes then low bytes (gzips better), and decodeCornerModel in sim/labscan/scanner.js widens
them back to fp32 in place. Everything else (graph, small tensors such as biases and Resize scales) is kept
byte for byte. INT8 was measured and rejected: up to 15 px error at 224 px.

  python3 tools/pack_corner_model.py path/to/doccornernet_lean.ort vendor/scanic-ml-0.2.0/doccornernet_lean.f16.bin

Source: npm scanic-ml@0.2.0 dist/doccornernet_lean.ort, sha256 732eb8d0...a80c8b3 (see SOURCE_SHA256).
Needs numpy and onnxruntime (for its ORT-format flatbuffer reader).

File layout (little endian): b"HCM1", u32 decoded length, u32 tensor count, count x (u32 byte offset, u32 values),
then the .ort bytes with those tensors' raw data removed, then the fp16 high-byte plane, then the low-byte plane.
"""
import hashlib, struct, sys

import numpy as np
from onnxruntime.tools.ort_format_model.ort_flatbuffers_py.fbs import InferenceSession

SOURCE_SHA256 = '732eb8d02d83cc63efb3f9467f01e0c458205a89b2547de3870bc6db1a80c8b3'
MIN_VALUES = 1024
FLOAT = 1  # TensorDataType.FLOAT


def weight_segments(model):
    graph = InferenceSession.InferenceSession.GetRootAs(model, 0).Model().Graph()
    segments = []
    for i in range(graph.InitializersLength()):
        tensor = graph.Initializers(i)
        if tensor.DataType() != FLOAT or tensor.RawDataLength() < 4 * MIN_VALUES:
            continue
        start = tensor._tab.Vector(tensor._tab.Offset(12))  # raw_data
        segments.append((start, tensor.RawDataLength() // 4))
    return sorted(segments)


def pack(model):
    segments = weight_segments(model)
    skeleton, halves, position = bytearray(), [], 0
    for start, count in segments:
        skeleton += model[position:start]
        halves.append(np.frombuffer(model, '<f4', count, start).astype('<f2'))
        position = start + 4 * count
    skeleton += model[position:]
    planes = np.concatenate(halves).view('u1').reshape(-1, 2)
    header = b'HCM1' + struct.pack('<II', len(model), len(segments)) + b''.join(struct.pack('<II', s, c) for s, c in segments)
    return header + bytes(skeleton) + planes[:, 1].tobytes() + planes[:, 0].tobytes()


def unpack(packed):
    """What the browser rebuilds (the reference for decodeCornerModel)."""
    assert packed[:4] == b'HCM1'
    length, n = struct.unpack_from('<II', packed, 4)
    segments = [struct.unpack_from('<II', packed, 12 + 8 * i) for i in range(n)]
    total = sum(c for _, c in segments)
    skeleton_at = 12 + 8 * n
    skeleton_len = length - 4 * total
    high = np.frombuffer(packed, 'u1', total, skeleton_at + skeleton_len)
    low = np.frombuffer(packed, 'u1', total, skeleton_at + skeleton_len + total)
    values = (high.astype('<u2') << 8 | low).view('<f2').astype('<f4')
    out, read, write, used = bytearray(length), skeleton_at, 0, 0
    for start, count in segments:
        out[write:start] = packed[read:read + start - write]
        read += start - write
        out[start:start + 4 * count] = values[used:used + count].tobytes()
        used += count
        write = start + 4 * count
    out[write:] = packed[read:skeleton_at + skeleton_len]
    return bytes(out)


if __name__ == '__main__':
    source, target = sys.argv[1], sys.argv[2]
    model = open(source, 'rb').read()
    if hashlib.sha256(model).hexdigest() != SOURCE_SHA256:
        sys.exit('not the scanic-ml 0.2.0 doccornernet_lean.ort this tool was measured on')
    packed = pack(model)
    rebuilt = unpack(packed)
    error = 0.0
    for start, count in weight_segments(model):
        a = np.frombuffer(model, '<f4', count, start)
        b = np.frombuffer(rebuilt, '<f4', count, start)
        error = max(error, float(np.max(np.abs(a - b) / np.maximum(np.abs(a), 6.2e-5))))
    open(target, 'wb').write(packed)
    print(f'{len(model)} -> {len(packed)} bytes; largest relative weight change {error:.2e}; '
          f'decoded sha256 {hashlib.sha256(rebuilt).hexdigest()}')
