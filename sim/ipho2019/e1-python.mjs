// Browser adapter only. All optical/state calculations execute the user's
// unmodified Python file in locally hosted CPython/WebAssembly (Pyodide).
import {loadPyodide} from '../../vendor/pyodide/pyodide.mjs';

const fields=['obj','order','tape_on','tape_held','tape_a','tape_b','ftape_a','ftape_b',
  'slider','laser_fine','hold_item','hold_rot','sel','level','laser_on','parchment',
  'dark','clock','t','lamp','n_disk','n_prism','lam_over_d','grating_id','prism_eps','prot_zero','_ph'];
const validPoint=value=>Array.isArray(value)&&value.length>=2&&value.slice(0,2).every(Number.isFinite);
const coverageKey=(x,y)=>`${x.toFixed(7)},${y.toFixed(7)}`;
let loading,runtime,create,dispatch,visibility,dispose,nextId=0;

async function readText(url){
  if(url.protocol==='file:'&&typeof process!=='undefined'&&process.versions?.node){
    const {readFile}=await import('node:fs/promises');return readFile(url,'utf8');
  }
  const response=await fetch(url);
  if(!response.ok)throw new Error(`Could not load Python experiment (${response.status}).`);
  return response.text();
}

export async function loadOriginalPython(){
  if(!loading)loading=(async()=>{
    const [source,bridge,python]=await Promise.all([
      readText(new URL('../../src/ipho2019_E1_sim_KO.py?v=dae656e74496',import.meta.url)),
      readText(new URL('./e1-bridge.py?v=592c604e954b',import.meta.url)),
      loadPyodide(),
    ]);
    runtime=python;runtime.globals.set('_hl_source',source);
    runtime.runPython(bridge);runtime.globals.delete('_hl_source');
    create=runtime.globals.get('_hl_new');dispatch=runtime.globals.get('_hl_dispatch');
    visibility=runtime.globals.get('_hl_vis');dispose=runtime.globals.get('_hl_dispose');
    return {version:runtime.version,python:runtime.runPython('sys.version.split()[0]')};
  })();
  return loading;
}

export function vis(intensity,dark){
  if(!visibility)throw new Error('Load the original Python experiment first.');
  return visibility(intensity,!!dark);
}

export class OpticalLab {
  constructor(options){
    if(!create)throw new Error('Call loadOriginalPython() before constructing an experiment.');
    this.seed=(typeof options==='object'&&options!==null?options.seed:options)??crypto.getRandomValues(new Uint32Array(1))[0];
    if(!Number.isSafeInteger(this.seed))throw new TypeError('Seed must be a safe integer.');
    this._id=++nextId;this._adopt(create(this._id,this.seed));
  }
  _state(){return JSON.stringify(Object.fromEntries(fields.filter(key=>this[key]!==undefined).map(key=>[key,this[key]])));}
  _adopt(json){
    const snapshot=JSON.parse(json);Object.assign(this,snapshot.state);this._frame=snapshot.frame;
    this._coverage=new Map((snapshot.frame.ruler8_samples||[]).map(([x,y,value])=>[coverageKey(x,y),value]));
    this._synced=this._state();return snapshot.result;
  }
  _call(method,...args){return this._adopt(dispatch(this._id,this._state(),method,JSON.stringify(args)));}
  _get(key){if(this._synced!==this._state())this._call('refresh');return this._frame[key];}
  clearPoseCache(){this._synced=null;}
  raise_(key){this._call('raise_',key);}
  pose(key){const value=this._get('poses')[key];if(!value)throw new RangeError('Unknown apparatus');return value;}
  pivot(){return this._get('pivot');}
  laser(){return this._get('laser');}
  beam_dir(){return this._get('beam_dir');}
  disk_center(){return this._get('disk_center');}
  prism_poly(){return this._get('prism_poly');}
  grating_seg(){return this._get('grating_seg');}
  screen_seg(){return this._get('screen_seg');}
  light_phase(){return this._get('light_phase');}
  slider_limits(){return this._get('slider_limits');}
  active(){return this._get('active');}
  wobbly(){return this._get('wobbly');}
  local(key,x,y){return this._call('local',key,x,y);}
  inside(key,x,y){return this._call('inside',key,x,y);}
  protractor(point){return this._call('protractor',point);}
  in_ruler8(x,y){
    if(!this.obj.ruler8.on)return false;
    this._get('poses');const key=coverageKey(x,y);
    if(this._coverage.has(key))return this._coverage.get(key);
    return this._call('in_ruler8',x,y);
  }
  trace(){
    const trace=this._call('trace');
    this.segs=trace.segments;this.spots=trace.spots;this.hits=trace.hits;this.shots=trace.shots;
    return trace;
  }
  setMounted(key,on=true,position=null){
    if(key!=='tape'&&!this.obj[key])return false;
    if(position!==null&&!validPoint(position))return false;
    return this._call('setMounted',key,!!on,position?.slice(0,2)??null);
  }
  toggle(key,position=null){return this.setMounted(key,key==='tape'?!this.tape_on:!this.obj[key]?.on,position);}
  move(key,position,{removeOutside=true}={}){
    if(!validPoint(position))return false;
    return this._call('move',key,position.slice(0,2),!!removeOutside);
  }
  rotate(key,delta){if(!Number.isFinite(delta))return false;return this._call('rotate',key,delta);}
  setSlider(value){return Number.isFinite(value)?this._call('setSlider',value):this.slider;}
  peelTape(key,index){if(!Number.isInteger(index))return false;return this._call('peelTape',key,index);}
  stickTape(x,y){if(!Number.isFinite(x)||!Number.isFinite(y))return false;return this._call('stickTape',x,y);}
  moveTapeEndpoint(key,position,{removeOutside=true}={}){
    if(!['tape_a','tape_b','ftape_a','ftape_b'].includes(key)||!validPoint(position))return false;
    return this._call('moveTapeEndpoint',key,position.slice(0,2),!!removeOutside);
  }
  advance(dt,scale=1){
    if(!Number.isFinite(dt)||dt<0||!Number.isFinite(scale)||scale<0)throw new RangeError('Time step must be finite and nonnegative');
    return this._call('advance',dt,scale);
  }
  dispose(){if(this._id){dispose(this._id);this._id=null;}}
}
