from pathlib import Path
import hashlib
B=Path('D:\\CodexBuilds\\Hasla-original-style-20261031\\izho2010-complete-solutions\\figure-language')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
