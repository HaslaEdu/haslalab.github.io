from pathlib import Path
import hashlib
ROOT=Path('D:/CodexBuilds/Hasla-poi-natural-20261102/style-corrections/icho2024-20261103')
SOURCE=ROOT/'frozen/source/IChO_2024_T_EN.pdf'
SOURCE_SHA='959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a'
PROOFS=None
def assert_output(path,n):
 path=Path(path).resolve()
 assert n in range(1,63)and path.name==f'page{n:02}.pdf'and path.is_relative_to(ROOT/'final/2024-v3')
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
