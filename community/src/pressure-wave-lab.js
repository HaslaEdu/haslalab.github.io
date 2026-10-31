/**
 * Private server-side instrument for the monthly pressure-wave experiment.
 * Never publish this file as a static browser asset.
 *
 * This is the stated first-wave, slowly varying rigid-pipe approximation,
 * not a general water-hammer solver. The incident ramp and its first
 * pressure-release reflection are superposed. Recording stops before the
 * reflected wave returns to the closed valve, where a further reflection
 * would require the next part of the model.
 *
 * All command results are instrument readings. Parameters that students
 * infer (diameter, elastic modulus and taper coefficients) are not returned.
 */

export const SENSOR_POSITIONS = Object.freeze(Array.from({length:8},(_,i)=>i*15));
export const CLOSURE_TIMES_MS = Object.freeze([2,5,10,20,50]);
export const SAMPLE_INTERVAL_MS = 0.10;
export const RECORD_START_MS = -3;
export const RECORD_DURATION_MS = 160;
export const MAX_RUNS = 100;
export const MAX_CALIBRATIONS = 200;

const LENGTH = 120;
const DENSITY = 1000;
const TIME_OFFSET_MS = .30;
const READ_WINDOW_MS = 3;
const FIXED_HEAD_M = 20;
const GRAVITY = 9.81;

function round(value,places=1){const factor=10**places;return Math.round((value+Number.EPSILON)*factor)/factor;}
function clone(value){return JSON.parse(JSON.stringify(value));}
function ramp(value){return Math.max(0,Math.min(1,value));}
function diameter(x,model){const u=x/LENGTH;return model.D0*(1+model.a*u+model.b*u*u);}
function area(x,model){return Math.PI*diameter(x,model)**2/4;}
function hashSeed(seed){
  let hash=2166136261;
  for(const c of String(seed)){hash^=c.charCodeAt(0);hash=Math.imul(hash,16777619);}
  return hash>>>0||1;
}
// The competitive instrument is unique to its private server session. Only
// observations leave the Worker; the seed and these parameters are never in a
// browser asset, HTTP response or saved public answer-sheet metadata.
export function pressureWaveParameters(seed){
  let state=hashSeed('model:'+seed);
  const random=()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return(state+.5)/4294967296;};
  return {D0:.048+.006*random(),a:.06+.04*random(),b:.025+.030*random(),K:2.05e9+.25e9*random(),Q:.000135+.000030*random()};
}
export function pressureWaveReference(seed){
  const p=pressureWaveParameters(seed),c=Math.sqrt(p.K/DENSITY),P0=DENSITY*c*p.Q/area(0,p)/1000;
  const gradient=2*(p.a+2*p.b)/(LENGTH*(1+p.a+p.b));
  const tauModel=.020/(c*gradient)*1000,tauEcho=2*(LENGTH-105)/c*1000-READ_WINDOW_MS;
  return {rho_kg_m3:DENSITY,L_m:LENGTH,K_Pa:p.K,c_m_s:c,D0_mm:p.D0*1000,a:p.a,b:p.b,Q0_L_s:p.Q*1000,
    D60_mm:diameter(60,p)*1000,D120_mm:diameter(120,p)*1000,
    t_off_ms:TIME_OFFSET_MS,P0_kPa:P0,max_dlnA_dx_per_m:gradient,tau_model_max_ms:tauModel,tau_echo_max_ms:tauEcho,
    selected_tau_ms:Math.max(...CLOSURE_TIMES_MS.filter(tau=>tau<=tauModel&&tau<tauEcho)),
    sensor_table:SENSOR_POSITIONS.map((x,i)=>({sensor:`S${i}`,x_m:x,D_mm:diameter(x,p)*1000,
      incident_P_kPa:P0*p.D0/diameter(x,p),arrival_ms:TIME_OFFSET_MS+1000*x/c})),
    uncertainty_floors:{pressure_kPa:.1/Math.sqrt(12),arrival_ms:.1/Math.sqrt(12),flow_L_s:.0001/Math.sqrt(12)}};
}
function numberArgument(token){
  if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(token||''))return null;
  const number=Number(token);return Number.isFinite(number)?number:null;
}
function formatTable(head,rows){
  const cells=[head,...rows].map(row=>row.map(String));
  const widths=head.map((_,i)=>Math.max(...cells.map(row=>row[i].length)));
  return cells.map((row,i)=>row.map((v,j)=>v.padStart(widths[j])).join('  ')+(i===0?'\n'+widths.map(n=>'-'.repeat(n)).join('  '):'')).join('\n');
}
function error(text){return{ok:false,text:`오류: ${text}`};}
function describe(values){
  const n=values.length,origin=values[0],mean=origin+values.reduce((sum,value)=>sum+(value-origin),0)/n;
  const s=n>1?Math.sqrt(values.reduce((sum,value)=>sum+(value-mean)**2,0)/(n-1)):null;
  return{n,mean,s,sem:s===null?null:s/Math.sqrt(n)};
}
function statisticText(stat,places=4){return[stat.mean,stat.s,stat.sem].map(value=>value===null?'-':value.toFixed(places));}
function selectedIds(token){
  if(token===undefined)return null;
  const ids=[];
  for(const item of token.split(',')){
    const match=/^([1-9]\d*)(?:-([1-9]\d*))?$/.exec(item);if(!match)return false;
    const start=Number(match[1]),end=Number(match[2]||match[1]);
    if(end<start||end>MAX_RUNS)return false;
    for(let id=start;id<=end;id++)ids.push(id);
  }
  return ids.length&&new Set(ids).size===ids.length?ids:false;
}

export class PressureWaveLab {
  #state;
  #model;
  #sensors;
  #records=[];
  #calibrations=[];
  #close=5;
  constructor({seed='server-instrument-test',parameters=pressureWaveParameters(seed)}={}){
    if(!parameters||![parameters.D0,parameters.a,parameters.b,parameters.K,parameters.Q].every(Number.isFinite)||parameters.D0<=0||parameters.K<=0||parameters.Q<=0)throw Error('Invalid server instrument model');
    this.#model={...parameters,c:Math.sqrt(parameters.K/DENSITY)};
    this.#state=hashSeed(seed);
    this.#sensors=SENSOR_POSITIONS.map((x,index)=>({
      id:`S${index}`,x,gain:1+(.016*this.#random()-.008),offset:round(.8*this.#random()-.4,2),
    }));
  }
  #random(){this.#state=(Math.imul(1664525,this.#state)+1013904223)>>>0;return(this.#state+.5)/4294967296;}
  #noise(sd){return sd*Math.sqrt(-2*Math.log(this.#random()))*Math.cos(2*Math.PI*this.#random());}
  #instrument(sensor,pressure){return round(sensor.gain*pressure+sensor.offset+this.#noise(.016),1);}
  #base(sensor){const velocity=this.#model.Q/area(sensor.x,this.#model);return(DENSITY*GRAVITY*FIXED_HEAD_M-.5*DENSITY*velocity**2)/1000;}
  #pressure(sensor,timeMs,closeMs){
    const direct=TIME_OFFSET_MS+1000*sensor.x/this.#model.c;
    const reflected=TIME_OFFSET_MS+1000*(2*LENGTH-sensor.x)/this.#model.c;
    const launch=DENSITY*this.#model.c*this.#model.Q/area(0,this.#model)/1000;
    const amplitude=launch*this.#model.D0/diameter(sensor.x,this.#model);
    return this.#base(sensor)+amplitude*(ramp((timeMs-direct)/closeMs)-ramp((timeMs-reflected)/closeMs));
  }
  #resolveRun(token){
    if(token===undefined)return this.#records.at(-1);
    if(!/^[1-9]\d*$/.test(token))return undefined;
    return this.#records.find(row=>row.summary.id===Number(token));
  }
  #readText(summary){
    return `RUN ${summary.id} | 폐쇄 ${summary.close_ms.toFixed(1)} ms | 초기 유량 ${summary.flow_L_s.toFixed(4)} L/s\n`+
      '단위: 도달·읽기 구간 ms, 표시 압력 kPa (미보정 게이지압)\n'+
      formatTable(['센서','x(m)','첫 도달','상승 전 r','상승 후 r','읽기 구간','분리'],summary.sensors.map(s=>[
        s.id,s.x_m.toFixed(1),s.arrival_ms.toFixed(2),s.before_kPa.toFixed(1),s.after_kPa.toFixed(1),
        `${s.read_start_ms.toFixed(2)}..${s.read_end_ms.toFixed(2)}`,s.isolated?'가능':'반사 겹침',
      ]))+'\n상승 전 값은 [-3.00, 0.00) ms, 상승 후 값은 표의 [읽기 시작, 읽기 끝) 구간에 저장된 표본의 평균입니다.'+
      '\n첫 도달은 같은 시계에 연결된 별도 트리거의 계측값입니다. 표시 압력은 센서 보정 전 값입니다.';
  }
  #generateTrace(close){
    return this.#sensors.map(sensor=>({
      sensor:sensor.id,x_m:sensor.x,
      points:Array.from({length:Math.round((RECORD_DURATION_MS-RECORD_START_MS)/SAMPLE_INTERVAL_MS)+1},(_,i)=>{
        const time=round(RECORD_START_MS+i*SAMPLE_INTERVAL_MS,2);
        return{t_ms:time,r_kPa:this.#instrument(sensor,this.#pressure(sensor,time,close))};
      }),
    }));
  }
  #traceFor(record){
    const current=this.#state;this.#state=record.traceSeed;
    try{return this.#generateTrace(record.summary.close_ms);}finally{this.#state=current;}
  }
  #run(){
    if(this.#records.length>=MAX_RUNS)return error(`측정 기록은 ${MAX_RUNS}회까지 보관합니다. 기존 기록은 read, trace, export로 열람할 수 있습니다.`);
    const close=this.#close;
    const traceSeed=this.#state,trace=this.#generateTrace(close);
    const sensors=this.#sensors.map((sensor,index)=>{
      // Arrival is an independent synchronised trigger reading, not a
      // threshold fitted to this sensor's quantised pressure samples.
      const arrival=round(TIME_OFFSET_MS+1000*sensor.x/this.#model.c+this.#noise(.025),1);
      const start=round(arrival+close,2),end=round(start+READ_WINDOW_MS,2);
      // A fixed window is used, rather than silently replacing overlapped data
      // with the ideal incident amplitude when a slow closure is selected.
      // Read and export must describe one acquisition: average the actual
      // saved samples, not an additional noisy synthetic measurement.
      const after=trace[index].points.filter(p=>p.t_ms>=start&&p.t_ms<end).map(p=>p.r_kPa);
      const before=trace[index].points.filter(p=>p.t_ms>=RECORD_START_MS&&p.t_ms<0).map(p=>p.r_kPa);
      return{id:sensor.id,x_m:sensor.x,arrival_ms:arrival,
        before_kPa:round(before.reduce((a,b)=>a+b,0)/before.length,1),
        after_kPa:round(after.reduce((a,b)=>a+b,0)/after.length,1),
        before_start_ms:RECORD_START_MS,before_end_ms:0,before_samples:before.length,read_samples:after.length,
        read_start_ms:start,read_end_ms:end,
        isolated:close+READ_WINDOW_MS<1000*2*(LENGTH-sensor.x)/this.#model.c,
      };
    });
    const summary={id:this.#records.length+1,close_ms:close,flow_L_s:round(this.#model.Q*1000+this.#noise(.00012),4),
      sample_ms:SAMPLE_INTERVAL_MS,start_ms:RECORD_START_MS,duration_ms:RECORD_DURATION_MS,sensors};
    this.#records.push({summary,traceSeed});
    return{ok:true,text:this.#readText(summary),run:clone(summary)};
  }
  #calibrationStatistics(reference){
    const records=this.#calibrations.filter(row=>reference===undefined||row.reference_kPa===reference);
    if(!records.length)return error('해당 보정 기록이 없습니다. cal 0 또는 cal 200으로 측정하세요.');
    const groups=[...new Set(records.map(row=>row.reference_kPa))].sort((a,b)=>a-b).map(pressure=>{
      const rows=records.filter(row=>row.reference_kPa===pressure);
      return{reference_kPa:pressure,n:rows.length,cal_ids:rows.map(row=>row.id),
        sensors:this.#sensors.map((sensor,index)=>({id:sensor.id,x_m:sensor.x,r_kPa:describe(rows.map(row=>row.sensors[index].r_kPa))}))};
    });
    const text=groups.map(group=>`기준압 ${group.reference_kPa.toFixed(1)} kPa | CAL 기록 ${group.n}개 | ID ${group.cal_ids.join(',')}\n`+
      formatTable(['센서','n','평균 r(kPa)','s(kPa)','SEM(kPa)'],group.sensors.map(sensor=>[sensor.id,sensor.r_kPa.n,...statisticText(sensor.r_kPa)]))).join('\n\n');
    return{ok:true,text:text+'\nSEM = s/√n. n=1이면 s와 SEM은 정의되지 않아 -로 표시합니다. 분해능에 따른 불확도는 별도 성분입니다.',calibrationStatistics:clone(groups)};
  }
  #statistics(close,ids){
    const records=this.#records.filter(row=>(close===undefined||row.summary.close_ms===close)&&(!ids||ids.includes(row.summary.id)));
    if(!records.length||ids&&records.length!==ids.length)return error('선택한 RUN과 폐쇄 시간이 일치하지 않습니다. history로 기록을 확인하세요.');
    const groups=[...new Set(records.map(row=>row.summary.close_ms))].sort((a,b)=>a-b).map(value=>{
      const rows=records.filter(row=>row.summary.close_ms===value);
      return{close_ms:value,n:rows.length,run_ids:rows.map(row=>row.summary.id),flow_L_s:describe(rows.map(row=>row.summary.flow_L_s)),
        sensors:this.#sensors.map((sensor,index)=>({id:sensor.id,x_m:sensor.x,
          arrival_ms:describe(rows.map(row=>row.summary.sensors[index].arrival_ms)),
          before_kPa:describe(rows.map(row=>row.summary.sensors[index].before_kPa)),
          after_kPa:describe(rows.map(row=>row.summary.sensors[index].after_kPa)),
          delta_raw_kPa:describe(rows.map(row=>row.summary.sensors[index].after_kPa-row.summary.sensors[index].before_kPa)),
          isolated:rows.every(row=>row.summary.sensors[index].isolated),
        }))};
    });
    const text=groups.map(group=>`폐쇄 ${group.close_ms.toFixed(1)} ms | RUN 기록 ${group.n}개 | ID ${group.run_ids.join(',')}\n`+
      `유량 평균/s/SEM (L/s): ${statisticText(group.flow_L_s,7).join(' / ')}\n`+
      formatTable(['센서','n','평균 t(ms)','s_t','SEM_t','평균 Δr(kPa)','s_Δr','SEM_Δr','분리'],group.sensors.map(sensor=>[sensor.id,sensor.arrival_ms.n,...statisticText(sensor.arrival_ms),...statisticText(sensor.delta_raw_kPa),sensor.isolated?'가능':'반사 겹침']))).join('\n\n');
    return{ok:true,text:text+'\n각 센서는 같은 RUN에서 동시에 측정됩니다. 원시 표시값 통계이며 보정·지름 역산 결과가 아닙니다.\nSEM = s/√n. n=1이면 s와 SEM은 정의되지 않아 -로 표시합니다. 분해능: r 0.1 kPa, 도달 0.1 ms, 유량 0.0001 L/s. 반복 표준편차가 0이어도 측정 오차 0으로 해석하지 마세요.',statistics:clone(groups)};
  }
  #exportSummary(calOnly=false){
    if(!this.#calibrations.length&&(calOnly||!this.#records.length))return error('내보낼 기록이 없습니다. 먼저 보정 또는 run을 실행하세요.');
    const head=['type','record_id','reference_kPa','close_ms','sensor','x_m','r_kPa','arrival_ms','before_kPa','after_kPa','delta_raw_kPa','flow_L_s','isolated','read_start_ms','read_end_ms'];
    const rows=this.#calibrations.flatMap(cal=>cal.sensors.map(s=>['CAL',cal.id,cal.reference_kPa,'',s.id,s.x_m,s.r_kPa,'','','','','','','','']));
    if(!calOnly)for(const {summary:run}of this.#records)for(const s of run.sensors)rows.push(['RUN',run.id,'',run.close_ms,s.id,s.x_m,'',s.arrival_ms,s.before_kPa,s.after_kPa,round(s.after_kPa-s.before_kPa,1),run.flow_L_s,s.isolated?1:0,s.read_start_ms,s.read_end_ms]);
    return{ok:true,text:`교정·측정표 ${rows.length}행을 CSV로 내보냅니다. RUN/CAL ID로 기록을 구분하세요. 전체 파형은 export RUN번호를 사용하세요.`,
      csv:[head.join(','),...rows.map(row=>row.join(','))].join('\r\n')+'\r\n',filename:calOnly?'pressure-wave-calibrations.csv':'pressure-wave-all-records.csv'};
  }
  execute(command,{metadataOnly=false}={}){
    if(typeof command!=='string'||command.length>200||/[\r\n\0]/.test(command))return error('한 줄에 명령어 하나를 입력하세요.');
    let words=command.trim().split(/\s+/);if(!command.trim())return{ok:true,text:''};
    if(['./pipe-lab','pipe-lab'].includes(words[0]))words=words.slice(1);
    if(!words.length)words=['help'];
    const cmd=words[0].toLowerCase(),args=words.slice(1);
    if(cmd==='help'&&args.length===0)return{ok:true,text:[
      'pipe-lab | 압력파 측정 장치',
      '  cal 0          기준압 0.0 kPa에서 센서 표시값 읽기',
      '  cal 200        기준압 200.0 kPa에서 센서 표시값 읽기',
      '  cal history    보관된 CAL 목록',
      '  cal stats [0|200] 교정값의 n, 평균, 표본 s, SEM',
      '  set close 5    폐쇄 시간 설정: 2, 5, 10, 20, 50 ms',
      '  run            같은 초기 유량으로 되돌린 후 1회 측정',
      '  read [번호]    최근 기록 또는 지정한 RUN의 측정표',
      '  trace S4 [번호] 센서 S0..S7의 시간-표시압 기록',
      '  history        보관된 RUN 목록',
      '  stats [ms] [RUN범위] 선택한 기록의 통계 (예: stats 5 1-3)',
      '  export [번호]  RUN의 전체 센서 기록을 CSV로 저장',
      '  export all     모든 CAL/RUN의 측정표 요약 CSV',
      '  export cal     교정 원자료 CSV',
      '  clear          터미널 화면 지우기 (기록 유지)',
      `표본 ${SAMPLE_INTERVAL_MS.toFixed(2)} ms, 기록 ${RECORD_START_MS}..${RECORD_DURATION_MS} ms, 최대 ${MAX_RUNS}회.`,
      '같은 RUN/CAL ID를 다시 읽으면 보관된 측정값을 반환합니다.',
      '첫 진행파와 수조에서 한 번 반사된 파를 사용하는 가상 장치입니다.',
    ].join('\n')};
    if(cmd==='clear'&&args.length===0)return{ok:true,text:'',clear:true};
    if(cmd==='cal'&&args.length===1&&args[0].toLowerCase()==='history'){
      const rows=this.#calibrations.map(row=>({id:row.id,reference_kPa:row.reference_kPa}));
      return{ok:true,text:rows.length?formatTable(['CAL','기준압(kPa)'],rows.map(row=>[row.id,row.reference_kPa.toFixed(1)])):'아직 보정 기록이 없습니다.',calibrationHistory:clone(rows)};
    }
    if(cmd==='cal'&&args[0]?.toLowerCase()==='stats'&&args.length<=2){
      const reference=args.length===2?numberArgument(args[1]):undefined;
      if(reference!==undefined&&reference!==0&&reference!==200)return error('cal stats, cal stats 0 또는 cal stats 200을 입력하세요.');
      return this.#calibrationStatistics(reference);
    }
    if(cmd==='cal'&&args.length===1){
      const pressure=numberArgument(args[0]);if(pressure!==0&&pressure!==200)return error('cal 0 또는 cal 200을 입력하세요. 단위는 kPa입니다.');
      if(this.#calibrations.length>=MAX_CALIBRATIONS)return error(`보정 기록은 ${MAX_CALIBRATIONS}개까지 보관합니다. 기존 기록은 cal history, cal stats, export cal로 열람할 수 있습니다.`);
      const calibration={id:this.#calibrations.length+1,reference_kPa:pressure,sensors:this.#sensors.map(s=>({id:s.id,x_m:s.x,r_kPa:this.#instrument(s,pressure)}))};
      this.#calibrations.push(calibration);
      return{ok:true,text:`CAL ${calibration.id} | 기준압 ${pressure.toFixed(1)} kPa\n`+formatTable(['센서','표시 r(kPa)'],calibration.sensors.map(s=>[s.id,s.r_kPa.toFixed(1)])),calibration:clone(calibration)};
    }
    if(cmd==='set'&&args.length===2&&args[0].toLowerCase()==='close'){
      const value=numberArgument(args[1]);if(!CLOSURE_TIMES_MS.includes(value))return error('폐쇄 시간은 2, 5, 10, 20, 50 ms 중 하나를 입력하세요.');
      this.#close=value;return{ok:true,text:`폐쇄 시간 τ = ${value.toFixed(1)} ms로 설정했습니다. 기존 기록은 유지됩니다.`,close_ms:value};
    }
    if(cmd==='run'&&args.length===0)return this.#run();
    if(cmd==='history'&&args.length===0){
      const history=this.#records.map(({summary:s})=>({id:s.id,close_ms:s.close_ms,flow_L_s:s.flow_L_s}));
      return{ok:true,text:history.length?formatTable(['RUN','폐쇄(ms)','유량(L/s)'],history.map(s=>[s.id,s.close_ms.toFixed(1),s.flow_L_s.toFixed(4)])):'아직 기록이 없습니다. run을 입력하세요.',history:clone(history)};
    }
    if(cmd==='stats'&&args.length<=2){
      const close=args.length?numberArgument(args[0]):undefined,ids=selectedIds(args[1]);
      if(close!==undefined&&!CLOSURE_TIMES_MS.includes(close)||ids===false)return error('stats [2|5|10|20|50] [RUN범위] 형식입니다. 예: stats 5 1-3. 중복 ID는 사용할 수 없습니다.');
      return this.#statistics(close,ids);
    }
    if(cmd==='export'&&args.length===1&&['all','cal'].includes(args[0].toLowerCase()))return this.#exportSummary(args[0].toLowerCase()==='cal');
    if((cmd==='read'||cmd==='export')&&args.length<=1){
      const record=this.#resolveRun(args[0]);if(!record)return error('해당 기록이 없습니다. history로 번호를 확인하거나 run으로 측정하세요.');
      if(cmd==='read')return{ok:true,text:this.#readText(record.summary),run:clone(record.summary)};
      if(metadataOnly)return{ok:true,text:`RUN ${record.summary.id}: ${Math.round((RECORD_DURATION_MS-RECORD_START_MS)/SAMPLE_INTERVAL_MS)+1}개 시각의 전체 센서 표시값을 CSV로 내보냅니다.`};
      const trace=this.#traceFor(record);
      const header=['run','close_ms','flow_L_s','t_ms',...this.#sensors.map(s=>`${s.id}_raw_kPa`)];
      const rows=trace[0].points.map((p,i)=>[record.summary.id,record.summary.close_ms.toFixed(1),record.summary.flow_L_s.toFixed(4),p.t_ms.toFixed(2),...trace.map(s=>s.points[i].r_kPa.toFixed(1))]);
      return{ok:true,text:`RUN ${record.summary.id}: ${rows.length}개 시각의 전체 센서 표시값을 CSV로 내보냅니다.`,
        csv:[header.join(','),...rows.map(row=>row.join(','))].join('\r\n')+'\r\n',filename:`pressure-wave-run-${String(record.summary.id).padStart(3,'0')}.csv`};
    }
    if(cmd==='trace'&&(args.length===1||args.length===2)){
      const sensor=String(args[0]).toUpperCase();if(!/^S[0-7]$/.test(sensor))return error('센서는 S0부터 S7까지 있습니다. 예: trace S4');
      const record=this.#resolveRun(args[1]);if(!record)return error('해당 기록이 없습니다. 먼저 run을 입력하세요.');
      if(metadataOnly)return{ok:true,text:`RUN ${record.summary.id} / ${sensor}, x = ${SENSOR_POSITIONS[Number(sensor.slice(1))].toFixed(1)} m\n`+
        `${RECORD_START_MS.toFixed(2)}..${RECORD_DURATION_MS.toFixed(2)} ms, ${SAMPLE_INTERVAL_MS.toFixed(2)} ms 간격, ${Math.round((RECORD_DURATION_MS-RECORD_START_MS)/SAMPLE_INTERVAL_MS)+1}개 표본\n`+
        '세로축은 보정 전 센서 표시값 r(kPa)입니다.'};
      const data=this.#traceFor(record).find(s=>s.sensor===sensor);
      return{ok:true,text:`RUN ${record.summary.id} / ${sensor}, x = ${data.x_m.toFixed(1)} m\n`+
        `${RECORD_START_MS.toFixed(2)}..${RECORD_DURATION_MS.toFixed(2)} ms, ${SAMPLE_INTERVAL_MS.toFixed(2)} ms 간격, ${data.points.length}개 표본\n`+
        '세로축은 보정 전 센서 표시값 r(kPa)입니다.',
        trace:{run_id:record.summary.id,close_ms:record.summary.close_ms,...clone(data)}};
    }
    return error('명령을 확인하세요. help를 입력하면 형식과 단위를 볼 수 있습니다.');
  }
}
