"""Sequential isolated workers for the six early natural-spacing editions."""
import argparse,json,os,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-natural-spacing')
COUNTS={2010:5,2011:6,2013:4,2015:5,2016:6,2020:5}

def child(command,log):
    environment=dict(os.environ,PYTHONIOENCODING='utf-8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    with log.open('w',encoding='utf8')as output:
        result=subprocess.run([sys.executable,'-X','utf8',*command],cwd=ROOT,env=environment,
            stdout=output,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
    return result.returncode

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--years',nargs='+',type=int,default=list(COUNTS));p.add_argument('--existing-plans',action='store_true');a=p.parse_args()
    result=[]
    for year in a.years:
        folder=BUILD/str(year)/'T';folder.mkdir(parents=True,exist_ok=True)
        if not a.existing_plans:
            code=child(['tools/izho_natural_spacing_rebuild.py',str(year),'T','--prepare-only'],folder/'early-prepare.log')
            if code:raise RuntimeError(('Plan preparation failed',year))
        for page in range(1,COUNTS[year]+1):
            plan=folder/'plans'/f'page{page:02d}.json'
            build=child(['-c',"import sys;sys.path.insert(0,'tools');from izho_natural_spacing_rebuild import page_build;page_build(sys.argv[1])",str(plan)],folder/f'page{page:02d}.build.log')
            qa=None
            if not build:qa=child(['tools/izho_natural_spacing_qa.py',str(year),'T',str(page)],folder/f'page{page:02d}.audit.log')
            result.append(dict(year=year,kind='T',page=page,build_exit=build,audit_exit=qa))
            (BUILD/'early-six-batch-progress.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
            print(json.dumps(result[-1]),flush=True)

if __name__=='__main__':main()
