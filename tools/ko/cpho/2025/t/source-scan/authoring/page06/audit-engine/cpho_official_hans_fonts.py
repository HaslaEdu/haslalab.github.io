"""Extract the required Chinese font CAB from an official Microsoft FOD ISO.

HTTP Range reads avoid downloading the5GB disc. No installer, DISM, registry,
Windows font installation, or existing system font modification is performed.
The ISO/CAB/font bytes stay in the explicitly named task cache on D.
"""
from pathlib import Path
import hashlib,json,struct,urllib.request,io,sys,os,subprocess,shutil

URL='https://software-download.microsoft.com/download/pr/19041.1.191206-1406.vb_release_amd64fre_FOD-PACKAGES_OEM_PT1_amd64fre_MULTI.iso'
OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts')
FONT_SHA256={'simhei.ttf':'aa4560dd8fe5645745fed3ffa301c3ca4d6c03cbd738145b613303961ba733b8','simkai.ttf':'9dd76f7ab430edd091db24c3f18e71410325c1414141aad5fe67947873ffba06','simfang.ttf':'3e2d44b01c9a248a61bedae4f15c8aae501328b1f7adfe6e111a5da5aa5c5104'}
def font_face(name):
    directory=Path(os.environ.get('HASLA_OFFICIAL_HANS_FONT_DIR',str(OUT/'faces')))
    path=directory/name
    if not path.exists():raise FileNotFoundError('Acquire official task-only Chinese fonts first: '+str(path))
    if name in FONT_SHA256:assert hashlib.sha256(path.read_bytes()).hexdigest()==FONT_SHA256[name]
    return path
def chunk(start,length):
    req=urllib.request.Request(URL,headers={'Range':f'bytes={start}-{start+length-1}'})
    with urllib.request.urlopen(req,timeout=60)as response:
        expected=f'bytes {start}-{start+length-1}/'
        assert response.status==206 and response.headers['Content-Range'].startswith(expected),response.headers
        raw=response.read();assert len(raw)==length
        return raw

def directory(extent,size):
    data=chunk(extent*2048,size);rows=[];offset=0
    while offset<len(data):
        length=data[offset]
        if not length:offset=(offset//2048+1)*2048;continue
        record=data[offset:offset+length];offset+=length
        name=record[33:33+record[32]].decode('ascii','replace')
        rows.append(dict(name=name,extent=int.from_bytes(record[2:6],'little'),size=int.from_bytes(record[10:14],'little'),directory=bool(record[25]&2)))
    return rows

class RemoteISO(io.RawIOBase):
    length=5232975872
    blocksize=1024*1024
    def __init__(self):self.position=0;self.cache={};self.name=URL;self.mode='rb'
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        self.position=offset if whence==0 else self.position+offset if whence==1 else self.length+offset
        if self.position<0:raise ValueError('Negative ISO seek')
        return self.position
    def read(self,size=-1):
        if size<0:size=self.length-self.position
        size=min(size,self.length-self.position)
        if size>64*1024*1024:raise ValueError('Refuse accidental full ISO download')
        result=[]
        while size>0:
            block=self.position//self.blocksize;within=self.position%self.blocksize
            if block not in self.cache:
                path=OUT/f'range-{block:05}.bin'
                expected=min(self.blocksize,self.length-block*self.blocksize)
                if path.exists():raw=path.read_bytes();assert len(raw)==expected
                else:raw=chunk(block*self.blocksize,expected);path.write_bytes(raw)
                self.cache[block]=raw
            raw=self.cache[block];count=min(size,len(raw)-within);result.append(raw[within:within+count]);size-=count;self.position+=count
        return b''.join(result)

def udf_cab():
    libs=OUT.parent/'python-libs'
    if libs.exists():sys.path.insert(0,str(libs))
    import pycdlib
    iso=pycdlib.PyCdlib();remote=RemoteISO();iso.open_fp(remote);assert iso.has_udf()
    root,dirs,files=next(iso.walk(udf_path='/'))
    names=[name for name in files if'fonts-hans'in name.lower()]
    print('UDF font CAB names:',names,flush=True);found=[]
    for name in names:
        path=OUT/name
        if not path.exists():iso.get_file_from_iso(str(path),udf_path='/'+name,blocksize=4*1024*1024)
        raw=path.read_bytes();assert raw[:4]==b'MSCF'
        found.append(dict(name=name,path=str(path),size=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    iso.close();assert found
    return found

def extract_faces():
    """Expand signed CAB data into task directories, never install it."""
    data=json.loads((OUT/'acquisition.json').read_text('utf8'))
    extracted=OUT/'extracted';extracted.mkdir(exist_ok=True)
    faces=OUT/'faces';faces.mkdir(exist_ok=True)
    for item in data['files']:
        cab=Path(item['path']);assert hashlib.sha256(cab.read_bytes()).hexdigest()==item['sha256']
        subprocess.run(['expand.exe',str(cab),'-F:*',str(extracted)],check=True,stdout=subprocess.DEVNULL)
    from fontTools.ttLib import TTFont
    records=[]
    for path in extracted.rglob('*.ttf'):
        raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        if path.name.lower()in FONT_SHA256:assert digest==FONT_SHA256[path.name.lower()]
        shutil.copy2(path,faces/path.name)
        with TTFont(path)as font:
            records.append(dict(file=path.name,bytes=len(raw),sha256=digest,postscript_name=font['name'].getDebugName(6),
                version=font['name'].getDebugName(5),weight=font['OS/2'].usWeightClass,embedding_flags=font['OS/2'].fsType))
    (OUT/'fonts-provenance.json').write_text(json.dumps(records,indent=2)+'\n','utf8')
    assert len(records)==6

def acquire():
    OUT.mkdir(parents=True,exist_ok=True)
    pvd=chunk(32768,2048);assert pvd[:7]==b'\x01CD001\x01'
    record=pvd[156:190];root=directory(int.from_bytes(record[2:6],'little'),int.from_bytes(record[10:14],'little'))
    (OUT/'iso-root.json').write_text(json.dumps(root,indent=2)+'\n','utf8')
    found=[x for x in root if'FONTS-HANS'in x['name'].upper()]
    print('Font CAB directory entries:',found,flush=True)
    if not found:
        found=udf_cab()
        (OUT/'acquisition.json').write_text(json.dumps(dict(official_url=URL,method='Read-only UDF metadata and requested CAB byte extents over HTTP Range; no OS installation.',files=found),indent=2)+'\n','utf8')
        return
    for entry in found:
        name=entry['name'].split(';')[0];path=OUT/name
        if not path.exists():
            with path.open('wb')as target:
                for pos in range(0,entry['size'],4*1024*1024):target.write(chunk(entry['extent']*2048+pos,min(4*1024*1024,entry['size']-pos)))
        assert path.stat().st_size==entry['size']and path.read_bytes()[:4]==b'MSCF'
        entry.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),path=str(path))
    (OUT/'acquisition.json').write_text(json.dumps(dict(official_url=URL,method='Read-only ISO9660 directory plus exact CAB extent HTTP Range requests; no OS install.',files=found),indent=2)+'\n','utf8')

if __name__=='__main__':
    if not(OUT/'acquisition.json').exists():acquire()
    extract_faces()
