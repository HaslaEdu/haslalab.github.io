"""Read-only extraction of the original DengXian Latin family for 2024 prose.

No font installer is executed and no system fonts are changed. Full Microsoft
font files stay in the local compressed tmp cache; only needed glyph subsets
are embedded in the translated PDFs. Korean uses the separate official Noto
CJK static400/700 assets. The original PDF font resources are never edited.
"""
from pathlib import Path
import argparse, ctypes, hashlib, json, struct, subprocess, urllib.request
from ctypes import wintypes as w
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'tmp/original-style-repair/cpho2024/fonts-source'
URL = 'https://download.microsoft.com/download/4/0/9/4094aba6-1a50-4ffd-a8cc-846bd66573f0/eadengfontpack.exe'
PACK_SHA = '08ca36c8ac6be452523ffe38d82a7d60f227aea61ac9fda27a0a9ecdb5078aed'
FONT_SHA = {
    'DENG.TTF': 'a3057626822c986aff0d2c9ec3b90a1a64180f29cbbb5708116e0489ac3355f9',
    'DENGB.TTF': '67c6835218a991c0b3dc5ae9a04500f20dd9fe48f73f447cb5e6b1ce17f45c75',
}
SIMSUN_SHA = '7e4a627d017fb51162f205472c9096224db8407ab6dfa70c078e3bf4daa7bdd6'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font_paths():
    result = {}
    for name, expected in FONT_SHA.items():
        path = BASE / 'faces' / name
        if not path.is_file() or sha(path) != expected:
            raise FileNotFoundError('Verified DengXian face required; run python tools/cpho_2024_original_fonts.py acquire')
        font = TTFont(path)
        if font['OS/2'].fsType & 0x0102:
            raise ValueError('Font embedding/subsetting flags are incompatible')
        result[700 if name == 'DENGB.TTF' else 400] = path
        font.close()
    return result


def simsun_path():
    """Same original family, extracted from installed licensed collection.

    The embedded Chinese subset's nominal Latin cmap is not evidence that its
    glyph programs are real Latin outlines. Use the complete, verified face.
    This is a new translation resource; source fonts are never modified.
    """
    path = BASE / 'faces/SimSun-Regular.ttf'
    if not path.is_file() or sha(path) != SIMSUN_SHA:
        raise FileNotFoundError('Verified installed SimSun face required; see simsun-provenance.json')
    with TTFont(path) as font:
        if font['OS/2'].fsType & 0x0102:
            raise ValueError('SimSun embedding/subsetting flags are incompatible')
        if font['OS/2'].usWeightClass != 400:
            raise ValueError('Unexpected SimSun weight')
    return path


def extract_msi_cabinet(path, target):
    """Read MSI _Streams in database-read-only mode; execute no custom actions."""
    msi = ctypes.WinDLL('msi')
    U = w.UINT
    P = ctypes.POINTER(U)
    msi.MsiOpenDatabaseW.argtypes = [w.LPCWSTR, ctypes.c_void_p, P]
    msi.MsiDatabaseOpenViewW.argtypes = [U, w.LPCWSTR, P]
    msi.MsiViewExecute.argtypes = [U, U]
    msi.MsiViewFetch.argtypes = [U, P]
    msi.MsiRecordReadStream.argtypes = [U, U, ctypes.c_void_p, P]
    msi.MsiCloseHandle.argtypes = [U]

    def check(value):
        if value:
            raise OSError('Read-only MSI API returned ' + str(value))

    database, view = U(), U()
    check(msi.MsiOpenDatabaseW(str(path.resolve()), None, ctypes.byref(database)))
    try:
        check(msi.MsiDatabaseOpenViewW(database, 'SELECT `Data` FROM `_Streams`', ctypes.byref(view)))
        check(msi.MsiViewExecute(view, 0))
        while True:
            record = U()
            result = msi.MsiViewFetch(view, ctypes.byref(record))
            if result == 259:
                break
            check(result)
            try:
                head, count = ctypes.create_string_buffer(4), U(4)
                check(msi.MsiRecordReadStream(record, 1, head, ctypes.byref(count)))
                if head.raw[:count.value] != b'MSCF':
                    continue
                with target.open('wb') as output:
                    output.write(head.raw[:count.value])
                    buffer = ctypes.create_string_buffer(1024 * 1024)
                    while True:
                        count = U(len(buffer))
                        check(msi.MsiRecordReadStream(record, 1, buffer, ctypes.byref(count)))
                        if not count.value:
                            break
                        output.write(buffer.raw[:count.value])
                return
            finally:
                msi.MsiCloseHandle(record)
        raise ValueError('Font cabinet stream absent')
    finally:
        if view.value:
            msi.MsiCloseHandle(view)
        msi.MsiCloseHandle(database)


def acquire(discard_packages=False):
    BASE.mkdir(parents=True, exist_ok=True)
    pack = BASE / 'eadengfontpack.exe'
    if not pack.exists():
        with urllib.request.urlopen(URL, timeout=60) as response, pack.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    if sha(pack) != PACK_SHA:
        raise ValueError('Official font pack SHA mismatch')
    literal = str(pack).replace("'", "''")
    command = "$s=Get-AuthenticodeSignature -LiteralPath '" + literal + "'; [PSCustomObject]@{Status=$s.Status.ToString();Signer=$s.SignerCertificate.Subject}|ConvertTo-Json -Compress"
    signature = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', command], text=True))
    if signature['Status'] != 'Valid' or 'Microsoft Corporation' not in signature['Signer']:
        raise ValueError('Microsoft Authenticode verification failed')
    raw = pack.read_bytes()
    offset = raw.find(b'MSCF')
    if offset < 0:
        raise ValueError('Outer font cabinet absent')
    size = struct.unpack_from('<I', raw, offset + 8)[0]
    outer = BASE / 'embedded-0.cab'
    outer.write_bytes(raw[offset:offset + size])
    unpacked = BASE / 'outer'
    unpacked.mkdir(exist_ok=True)
    subprocess.run(['expand.exe', '-F:eadengfontpack.msi', str(outer), str(unpacked)], check=True)
    cabinet = BASE / 'font-data-0.cab'
    extract_msi_cabinet(unpacked / 'eadengfontpack.msi', cabinet)
    faces = BASE / 'faces'
    faces.mkdir(exist_ok=True)
    for name in FONT_SHA:
        subprocess.run(['expand.exe', '-F:' + name, str(cabinet), str(faces)], check=True)
    result = font_paths()
    if discard_packages:
        # Only these exact, replaceable archives; never original contest PDFs,
        # verified font faces, handwritten plans or final editions.
        for path in [pack, outer, cabinet, unpacked / 'eadengfontpack.msi']:
            if not path.resolve().is_relative_to(BASE.resolve()):
                raise ValueError('Cache deletion outside intended directory')
            if path.exists():
                path.unlink()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['verify', 'acquire'])
    parser.add_argument('--discard-packages', action='store_true')
    args = parser.parse_args()
    result = acquire(args.discard_packages) if args.command == 'acquire' else font_paths()
    print(json.dumps({str(k): str(v.relative_to(ROOT)) for k, v in result.items()}, ensure_ascii=False))
