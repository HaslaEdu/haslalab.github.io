# KPhE PDF font provenance

Verified 2026-10-30. The measured official-paper profiles are in `kphe_original_typography.json`. The 2026 body uses Gulim; the 2024 second-session expert body uses its original Haansoft Batang outlines.

Original font programs remain outside Git. `kphe_fonts.py` reads installed files from `KPHE_FONT_DIR` (default `C:/Windows/Fonts`) and writes derived fonts under its `CACHE` path in ignored `tmp/`.

| Font | Installed source |
| --- | --- |
| Gulim | `gulim.ttc`, face 0 |
| Batang / BatangChe | `batang.ttc`, faces 0 / 1 |
| HCRBatang, legacy-body fallback | `HANBatang.ttf` |
| HCRDotum-Bold | `HANDotumB.ttf` |
| HancomEQN | `HancomEQN.ttf` |
| HyhwpEQ, legacy expert equations | `HYHWPEQ.TTF` |
| Times New Roman Bold | `timesbd.ttf` |

`kphe_fonts.equation_fonts()` remaps the installed HancomEQN equation slots to Unicode while retaining the native outlines; Korean formula labels use Gulim outlines. `kphe_source_fonts.legacy_body_font()` retains the 2024 second-session expert paper's embedded body outlines and uses installed HCRBatang for additional explanation characters. `kphe_legacy_equations.py` retains the corresponding HyhwpEQ outlines. These derived cache files are also untracked.

KoPub header font: **KoPubDotum Bold**, internal PostScript name `KoPubDotumBold`, version 1.00. Retrieval mirror: [adrinerDP/font-kopub](https://github.com/adrinerDP/font-kopub/tree/8239dd7643e4f397e745e68c45dbb368989ceca0). The pinned file was downloaded again and compared with the build input:

- [Download KoPubDotum-Bold.ttf](https://raw.githubusercontent.com/adrinerDP/font-kopub/8239dd7643e4f397e745e68c45dbb368989ceca0/fonts/KoPubDotum-Bold.ttf)
- Bytes: `3092284`
- SHA-256: `a4af80d1f39298fb70c1cdd812dabe2f84000f1b02505563018198d035452977`
- [Mirror's license text](https://github.com/adrinerDP/font-kopub/blob/8239dd7643e4f397e745e68c45dbb368989ceca0/LICENSE.md)

To reproduce the header-font input, run the following Python from the repository root after installing the original Windows/Hancom fonts listed above. It uses the cache namespace selected by `kphe_fonts.py`:

```python
import hashlib, sys, urllib.request
sys.path.insert(0, 'tools')
from kphe_fonts import CACHE
url = 'https://raw.githubusercontent.com/adrinerDP/font-kopub/8239dd7643e4f397e745e68c45dbb368989ceca0/fonts/KoPubDotum-Bold.ttf'
data = urllib.request.urlopen(url).read()
assert hashlib.sha256(data).hexdigest() == 'a4af80d1f39298fb70c1cdd812dabe2f84000f1b02505563018198d035452977'
CACHE.mkdir(parents=True, exist_ok=True)
(CACHE / 'KoPubDotum-Bold.ttf').write_bytes(data)
```

Use a fresh Python process after changing source fonts or cache configuration; the font helpers memoize resolved paths. The PDF builders regenerate derived fonts as needed. Commit the code, provenance and resulting PDFs, leaving original and derived `.ttf`/`.ttc` files in their external/ignored locations.
