# EuPhO solutions in Korean

The Korean of every prose block of the official EuPhO theory solutions (2017–2026), laid over the original pages
with `tools/ko_reflow/block_overlay.py`:

    python3 -I tools/ko_reflow/block_overlay.py html EuPhO_2023_TS.pdf tools/ko_reflow/eupho/k2023.json k.html
    python3 -I tools/ko_reflow/build.py k.html k.src.pdf pdfx/eupho/EuPhO_2023_TS_KO.pdf

`EuPhO_<year>_TS.pdf` (or `EuPhO_<year>_T<n>S.pdf` for 2017–2018; `k18_1.json` is 2018 T1) is the original solution
from the PDF Worker. Equations, figures and numbers stay exactly as printed.
