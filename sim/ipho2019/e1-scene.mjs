import * as THREE from '../../vendor/three/three.module.js';
import { OrbitControls } from '../../vendor/three/OrbitControls.js';

// All apparatus coordinates and dimensions are centimetres. Physics x,y maps
// directly to scene x,z; scene y is height above the green mat. Positive device
// rotation has the original dirv(a)=[cos(a),-sin(a)] convention.
const DEG=Math.PI/180,ROOM_W=272,ROOM_D=208,LOW=2.2,HIGH=6.0;
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
const finite=n=>Number.isFinite(n);

export function createOpticalScene(container,options={}) {
  const geometries=new Set(),materials=new Set(),textures=new Set(),gcache=new Map(),mcache=new Map();
  const scene=new THREE.Scene();scene.background=new THREE.Color('#26352f');
  const camera=new THREE.PerspectiveCamera(42,1,.15,1300);
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
  renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio||1,1.7));
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.88;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  const canvas=renderer.domElement;canvas.style.cssText='display:block;width:100%;height:100%;touch-action:none;outline-offset:-3px';
  canvas.tabIndex=0;canvas.setAttribute('aria-label',options.language==='en'?'3D optical bench. Drag apparatus to move; Shift-drag to turn. Drag the mat to orbit.':'3D 광학 실험대. 장비를 끌어 이동하고 Shift를 누르고 끌어 회전합니다. 바닥을 끌어 시점을 바꿉니다.');
  container.append(canvas);
  const controls=new OrbitControls(camera,canvas);controls.target.set(136,1,130);camera.position.copy(controls.target).add(new THREE.Vector3(.23,.68,.70).normalize().multiplyScalar(150));
  controls.enableDamping=true;controls.dampingFactor=.12;controls.minDistance=13;controls.maxDistance=550;
  controls.maxPolarAngle=Math.PI*.49;controls.minPolarAngle=.018;controls.screenSpacePanning=false;
  controls.mouseButtons.LEFT=THREE.MOUSE.ROTATE;controls.mouseButtons.RIGHT=THREE.MOUSE.PAN;
  let lab=null,lastTrace=null,disposed=false,frame=0,selectedKey=null,viewMode='perspective',lastDark=null,protractorZero=null,warmed=false,initialFit=true;
  const roots={},pickables=[],pointer=new THREE.Vector2(),ray=new THREE.Raycaster(),ground=new THREE.Plane(new THREE.Vector3(0,1,0),0);
  const groundPoint=new THREE.Vector3(),dragPointers=new Map();let action=null,gesture=null;
  const geo=(key,build)=>{if(!gcache.has(key)){const value=build();gcache.set(key,value);geometries.add(value);}return gcache.get(key);};
  const material=(key,parameters)=>{if(!mcache.has(key)){const value=new THREE.MeshStandardMaterial(parameters);mcache.set(key,value);materials.add(value);}return mcache.get(key);};
  const mat={
    aluminium:material('aluminium',{color:'#c5cacf',metalness:.30,roughness:.44}),edge:material('edge',{color:'#b8bfc5',metalness:.25,roughness:.50}),
    black:material('black',{color:'#1c1e21',roughness:.65}),rubber:material('rubber',{color:'#111214',roughness:.9}),red:material('red',{color:'#cf3029',roughness:.58}),
    brass:material('brass',{color:'#b59a43',metalness:.67,roughness:.35}),white:material('white',{color:'#eeeee9',roughness:.85}),
    wood:material('wood',{color:'#c9a878',roughness:.86}),ply:material('ply',{color:'#ad9572',roughness:.91}),blue:material('blue',{color:'#234986',roughness:.55}),
    pink:material('pink',{color:'#e4407d',roughness:.48}),yellow:material('yellow',{color:'#eacc32',roughness:.5}),paper:material('paper',{color:'#ece5d0',roughness:.95}),
  };
  const glass=new THREE.MeshPhysicalMaterial({color:'#d8edef',transparent:true,opacity:.36,roughness:.1,metalness:.05,clearcoat:1,clearcoatRoughness:.1,side:THREE.DoubleSide,depthWrite:false});materials.add(glass);
  const plastic=new THREE.MeshPhysicalMaterial({color:'#dce9ec',transparent:true,opacity:.24,roughness:.2,clearcoat:.8,depthWrite:false});materials.add(plastic);
  const boxGeometry=geo('box',()=>new THREE.BoxGeometry(1,1,1)),cylinderGeometry=geo('cylinder',()=>new THREE.CylinderGeometry(1,1,1,48));
  function mesh(parent,geometry,material,position=[0,0,0],scale=[1,1,1],hit){
    const value=new THREE.Mesh(geometry,material);value.position.set(...position);value.scale.set(...scale);value.castShadow=true;value.receiveShadow=true;
    if(hit)value.userData.hit=hit;parent.add(value);return value;
  }
  const box=(parent,dimensions,position,material,hit)=>mesh(parent,boxGeometry,material,position,dimensions,hit);
  const cylinder=(parent,radius,height,position,material,hit)=>mesh(parent,cylinderGeometry,material,position,[radius,height,radius],hit);
  function tube(parent,points,radius,material,hit){
    const path=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p))),geometry=new THREE.TubeGeometry(path,18,radius,6,false);geometries.add(geometry);return mesh(parent,geometry,material,[0,0,0],[1,1,1],hit);
  }
  const printedMaterials=new Set();
  function canvasTexture(width,height,draw){
    const image=document.createElement('canvas');image.width=width;image.height=height;const context=image.getContext('2d');draw(context,width,height);
    const texture=new THREE.CanvasTexture(image);texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=Math.min(16,renderer.capabilities.getMaxAnisotropy());textures.add(texture);return texture;
  }
  function printedMaterial(texture,transparent=false){const value=new THREE.MeshBasicMaterial({map:texture,color:'#ffffff',toneMapped:false,transparent,side:THREE.DoubleSide,depthWrite:!transparent});materials.add(value);printedMaterials.add(value);return value;}
  function horizontal(parent,width,depth,height,material,hit){const value=mesh(parent,geo('plane',()=>new THREE.PlaneGeometry(1,1)),material,[0,height,0],[width,depth,1],hit);value.rotation.x=-Math.PI/2;value.castShadow=false;return value;}
  function label(parent,text,x,y,z,width=4){
    const key='label:'+text;let value=mcache.get(key);
    if(!value){const map=canvasTexture(384,96,(c,w,h)=>{c.fillStyle='rgba(248,247,238,.94)';c.fillRect(0,0,w,h);c.strokeStyle='#918d7e';c.lineWidth=3;c.strokeRect(1,1,w-2,h-2);c.font='600 57px Arial, sans-serif';c.textAlign='center';c.textBaseline='middle';c.fillStyle='#282b29';c.fillText(text,w/2,h/2+2);});value=new THREE.SpriteMaterial({map,depthTest:true,depthWrite:false});materials.add(value);mcache.set(key,value);}
    const sprite=new THREE.Sprite(value);sprite.position.set(x,y,z);sprite.scale.set(width,width/4,1);parent.add(sprite);return sprite;
  }
  function printedRuler(length,width=4096,height=256,base='#e4e7e8',labels=1){
    return canvasTexture(width,height,(c,w,h)=>{
      c.fillStyle=base;c.fillRect(0,0,w,h);c.fillStyle='rgba(255,255,255,.28)';c.fillRect(0,h*.43,w,h*.16);
      for(let index=0;index<=Math.floor(length*10);index++){
        const x=index/10/length*w,major=index%10===0,half=index%5===0,long=major?.32:half?.22:.12;
        c.strokeStyle=major?'#252a2b':'#586264';c.lineWidth=major?1.7:1;c.beginPath();c.moveTo(x,0);c.lineTo(x,h*long);c.moveTo(x,h);c.lineTo(x,h*(1-long));c.stroke();
        if(major&&(index/10)%labels===0){c.font='500 '+Math.round(h*.22)+'px Arial, sans-serif';c.textAlign='center';c.textBaseline='middle';c.fillStyle='#292e30';c.fillText(String(index/10),x,h*.53);}
      }
      c.strokeStyle='#788487';c.lineWidth=2;c.strokeRect(1,1,w-2,h-2);
    });
  }
  // Green cutting mat and cubicle walls from the official equipment photographs.
  const matTexture=canvasTexture(1024,1024,(c,w,h)=>{
    c.fillStyle='#5f8b76';c.fillRect(0,0,w,h);let state=2319;
    for(let i=0;i<15000;i++){state=(state*1664525+1013904223)>>>0;const x=(state&1023);state=(state*1664525+1013904223)>>>0;const y=state&1023;c.fillStyle=i%2?'rgba(19,49,32,.022)':'rgba(247,255,246,.025)';c.fillRect(x,y,2,1);}
  });
  const matMaterial=material('green',{map:matTexture,color:'#ffffff',roughness:1});
  const table=new THREE.Group();table.position.set(ROOM_W/2,0,ROOM_D/2);scene.add(table);
  box(table,[ROOM_W+3,4,ROOM_D+3],[0,-2.05,0],material('tableedge',{color:'#354e40',roughness:.9}));horizontal(table,ROOM_W,ROOM_D,0,matMaterial);
  const wallMaterial=material('walls',{color:'#e9e2d2',roughness:1,side:THREE.FrontSide});
  const wallGeometry=geo('wall',()=>new THREE.PlaneGeometry(1,1));
  const back=mesh(scene,wallGeometry,wallMaterial,[136,24,0],[272,48,1]);back.castShadow=false;
  const left=mesh(scene,wallGeometry,wallMaterial,[0,24,104],[208,48,1]);left.rotation.y=Math.PI/2;left.castShadow=false;
  const right=mesh(scene,wallGeometry,wallMaterial,[272,24,104],[208,48,1]);right.rotation.y=-Math.PI/2;right.castShadow=false;
  const ambient=new THREE.HemisphereLight('#fff8e9','#254c36',1.35);scene.add(ambient);
  const keyLight=new THREE.DirectionalLight('#fff6df',1.85);keyLight.position.set(78,165,150);keyLight.target.position.set(136,0,108);scene.add(keyLight,keyLight.target);
  keyLight.castShadow=true;keyLight.shadow.mapSize.set(1024,1024);keyLight.shadow.camera.left=-155;keyLight.shadow.camera.right=155;keyLight.shadow.camera.top=135;keyLight.shadow.camera.bottom=-135;keyLight.shadow.camera.near=1;keyLight.shadow.camera.far=350;keyLight.shadow.bias=-.0005;keyLight.shadow.normalBias=.04;
  function root(key){const group=new THREE.Group();group.userData.hit={key};roots[key]=group;scene.add(group);pickables.push(group);return group;}
  const ruler=root('ruler');
  box(ruler,[60.8,.32,5.2],[0,.2,0],mat.aluminium);
  const rulerFace=horizontal(ruler,60,5.12,.365,printedMaterial(printedRuler(60)));rulerFace.position.x=0;
  box(ruler,[60,.12,.23],[0,.44,-2.48],mat.edge);box(ruler,[60,.12,.23],[0,.44,2.48],mat.edge);
  label(ruler,'1',27,.9,0,1.6);
  const slider=new THREE.Group();slider.userData.hit={key:'laser',role:'slider'};ruler.add(slider);
  for(const x of [-3.2,3.2]){
    box(slider,[3.4,.58,6],[x,.64,0],mat.red);
    box(slider,[1.8,.08,1.1],[x,.96,1.6],mat.white);
    for(let row=0;row<2;row++)for(let col=0;col<4;col++)cylinder(slider,.11,.08,[x-1.05+col*.7,.98,-.7-row*.9],material('redhole',{color:'#90221d',roughness:1}));
  }
  box(slider,[9.8,.3,5.4],[0,1.05,0],plastic);label(slider,'2',4.3,1.6,1.8,1.4);
  const head=new THREE.Group();head.userData.hit={key:'laser',role:'slider'};slider.add(head);
  box(head,[5.5,.25,7.3],[-.45,1.35,.85],mat.aluminium);
  box(head,[5.5,6.5,.38],[-.45,4.65,4.3],mat.edge);
  // AA battery pack, leads, thumbscrews, white diode clamp and direction bar.
  box(head,[4.9,3.2,1.45],[-.45,5.1,3.45],mat.black);
  for(const y of [4.45,5.85]){const battery=cylinder(head,.55,4.6,[-.45,y,3.45],material('battery',{color:'#323943',metalness:.6,roughness:.38}));battery.rotation.z=Math.PI/2;}
  const lowRedLead=tube(head,[[-2.4,5.8,3.9],[-3.0,4.5,1.8],[-1.3,3.1,-.4],[.5,2.2,-.9]],.075,mat.red);
  const lowBlackLead=tube(head,[[1.3,4.3,3.9],[2.4,3.6,2.2],[1.5,2.7,.3],[.5,2.2,-.9]],.075,mat.black);
  const highRedLead=tube(head,[[-2.4,5.8,3.9],[-2.9,7.3,1.8],[-1.3,7.5,-.4],[.5,6,-.9]],.075,mat.red);
  const highBlackLead=tube(head,[[1.3,4.3,3.9],[2.4,6.5,2.2],[1.5,6.8,.3],[.5,6,-.9]],.075,mat.black);
  cylinder(head,.93,.35,[0,1.65,0],mat.brass);
  cylinder(head,.32,.8,[2.55,1.82,1.2],mat.brass);
  const fineBar=cylinder(head,.235,15,[0,2.0,8.5],mat.brass,{key:'laser',role:'fine'});fineBar.rotation.x=Math.PI/2;label(head,'4C',.9,2.8,14.5,2.1);
  const diodeAssembly=new THREE.Group();diodeAssembly.userData.hit={key:'laser',role:'switch'};head.add(diodeAssembly);
  const diodeSupport=box(head,[.25,1,.7],[1.4,1.9,-2.1],mat.edge);
  const barrel=cylinder(diodeAssembly,.60,2.3,[0,0,-.15],mat.black);barrel.rotation.x=Math.PI/2;
  const clampGeometry=geo('diodeClamp',()=>{const shape=new THREE.Shape();shape.absarc(0,0,.77,0,Math.PI*2,false);const hole=new THREE.Path();hole.absarc(0,0,.61,0,Math.PI*2,true);shape.holes.push(hole);const geometry=new THREE.ExtrudeGeometry(shape,{depth:2.13,bevelEnabled:false,curveSegments:24});geometry.translate(0,0,-1.065);return geometry;});
  mesh(diodeAssembly,clampGeometry,mat.white,[0,0,-2.35]);
  const nozzle=cylinder(diodeAssembly,.40,1.7,[0,0,-2.12],mat.black);nozzle.rotation.x=Math.PI/2;
  box(diodeAssembly,[2.4,.55,.85],[.45,.7,-2.1],mat.white);
  cylinder(diodeAssembly,.2,.38,[1,.95,-2.1],mat.brass);
  const apertureMaterial=new THREE.MeshBasicMaterial({color:'#421811'});materials.add(apertureMaterial);
  const aperture=cylinder(diodeAssembly,.18,.05,[0,0,-2.91],apertureMaterial);aperture.rotation.x=Math.PI/2;aperture.castShadow=false;
  const switchBase=cylinder(head,.35,.55,[1.9,8.35,4.1],mat.brass,{key:'laser',role:'switch'});
  const switchTip=box(head,[.16,.8,.18],[1.9,8.95,4.1],mat.black,{key:'laser',role:'switch'});label(head,'3C',2.8,9.6,4.1,1.9);
  label(head,'4A',-2.6,2.3,1.7,1.8);label(head,'3',-2.1,5.0,-1.4,1.4);
  const disk=root('disk');box(disk,[30.4,.8,30.4],[0,.42,0],mat.wood);box(disk,[28.4,.12,28.4],[0,.88,0],mat.ply);
  const protractorMaterial=printedMaterial(canvasTexture(1024,1024,c=>c.clearRect(0,0,1024,1024)));
  horizontal(disk,26,26,1.02,protractorMaterial);
  cylinder(disk,10,2.4,[0,LOW,0],glass);
  const rim=mesh(disk,geo('diskRim',()=>new THREE.TorusGeometry(10,.045,6,96)),material('glassRim',{color:'#bddfe5',transparent:true,opacity:.68,roughness:.22}),[0,3.405,0]);rim.rotation.x=Math.PI/2;rim.castShadow=false;
  const parchment=cylinder(disk,10.16,2.7,[0,LOW,0],material('parchment',{color:'#e2d9c2',transparent:true,opacity:.52,roughness:1,side:THREE.DoubleSide,depthWrite:false}));
  parchment.geometry=geo('parchmentSide',()=>new THREE.CylinderGeometry(1,1,1,96,1,true));label(disk,'10',13.2,1.8,12.5,2.1);
  const holder=root('holder');box(holder,[25,.9,17],[0,.48,0],mat.wood);box(holder,[23,.14,15.2],[0,1.01,0],mat.white);
  cylinder(holder,4.4,1.5,[0,1.84,0],mat.black);
  const turning=new THREE.Group();turning.userData.hit={key:'holder12b',role:'holderRotate'};holder.add(turning);
  cylinder(turning,3.3,1.0,[0,3.05,0],mat.black);label(holder,'12A',10,1.8,5.7,2.5);
  const grating=new THREE.Group();turning.add(grating);
  box(grating,[7.0,1.7,.9],[0,3.95,0],mat.black);box(grating,[7.0,1.15,.9],[0,9.3,0],mat.black);
  box(grating,[1.1,4.6,.9],[-2.95,6.3,0],mat.black);box(grating,[1.1,4.6,.9],[2.95,6.3,0],mat.black);
  box(grating,[4.8,4.7,.12],[0,6.25,0],material('gratingGlass',{color:'#98bdaf',transparent:true,opacity:.35,roughness:.2,metalness:.1,depthWrite:false}));label(grating,'12C',0,10.7,0,2.6);
  label(turning,'12B',4.5,4,2.2,2.7);
  const prismGeometry=new THREE.BufferGeometry();prismGeometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(72),3));geometries.add(prismGeometry);
  const prism=mesh(turning,prismGeometry,glass);prism.userData.hit={key:'holder12b',role:'holderRotate'};label(prism,'12D',0,9.8,0,2.6);let prismShape='';
  // The official 12D photograph has a paper wrap on the lower prism faces.
  // It follows the actual specimen outline, entirely below the high beam.
  const prismBandGeometry=new THREE.BufferGeometry();prismBandGeometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(54),3));geometries.add(prismBandGeometry);
  const prismBand=mesh(turning,prismBandGeometry,mat.white);prismBand.userData.hit={key:'holder12b',role:'holderRotate'};
  const screen=root('screen');box(screen,[120,29,1.6],[0,14.5,0],mat.black);
  for(const x of [-50.4,50.4]){cylinder(screen,.65,5,[x,2.5,3.4],mat.black);box(screen,[9,.5,10],[x,.3,2.2],mat.edge);}
  label(screen,'5',57,30.5,0,2.5);
  const ruler8=root('ruler8');box(ruler8,[31.2,.32,3.8],[0,.23,0],plastic);
  const transparentScale=printedRuler(30,2048,256,'rgba(229,241,243,.14)',1),transparentScaleMat=printedMaterial(transparentScale,true);
  horizontal(ruler8,30,3.75,.4,transparentScaleMat);label(ruler8,'8',-14.5,.9,-1.9,1.5);
  const tape6=root('tape6');
  const rollGeometry=geo('roll',()=>{const shape=new THREE.Shape();shape.absarc(0,0,4,0,Math.PI*2,false);const hole=new THREE.Path();hole.absarc(0,0,2.3,0,Math.PI*2,true);shape.holes.push(hole);const geometry=new THREE.ExtrudeGeometry(shape,{depth:2.6,bevelEnabled:true,bevelThickness:.06,bevelSize:.06,bevelSegments:1,curveSegments:48});geometry.rotateX(-Math.PI/2);return geometry;});
  mesh(tape6,rollGeometry,mat.paper,[0,.04,0]);label(tape6,'6',4.8,2.5,0,1.5);
  // Office lamp (9), at the rear side of the work area. It is scenery, not an
  // extra optical element and never creates a laser path or changes the model.
  const lamp=new THREE.Group();lamp.position.set(253,0,185);scene.add(lamp);
  cylinder(lamp,5.0,.8,[0,.45,0],mat.blue);tube(lamp,[[0,1,0],[1,12,0],[-1.5,24,-1],[2,31,-4]],.45,mat.blue);
  const shade=mesh(lamp,geo('shade',()=>new THREE.CylinderGeometry(2.6,4.0,4,24,1,true)),mat.white,[2,30,-4]);shade.rotation.z=.3;
  cylinder(lamp,2.5,.6,[2,32.0,-4],mat.blue);label(lamp,'9',5.3,3,0,1.8);
  const bulbMaterial=material('lampBulb',{color:'#fff8e4',emissive:'#fff1c8',emissiveIntensity:0,roughness:.4});
  cylinder(lamp,2.7,.12,[2,28.1,-4],bulbMaterial);
  const lampLight=new THREE.SpotLight('#fff2d7',0,340,.8,.65,2);lampLight.position.set(255,28,181);lampLight.target.position.set(136,1,115);scene.add(lampLight,lampLight.target);
  const tape=new THREE.Group();scene.add(tape);pickables.push(tape);
  const tapeFace=horizontal(tape,1,3,.16,mat.paper,{key:'tape',role:'tapeBody'});
  const tapeCase=cylinder(tape,2.2,1.15,[0,.7,0],mat.pink,{key:'tape',role:'tapeEnd',end:'a'});cylinder(tape,.5,.14,[0,1.35,0],mat.yellow,{key:'tape',role:'tapeEnd',end:'a'});
  const tapeEnd=box(tape,[1.4,.5,3.3],[0,.4,0],mat.yellow,{key:'tape',role:'tapeEnd',end:'b'});label(tape,'7',0,2.5,3.1,1.5);
  const frontTape=new THREE.Group();screen.add(frontTape);
  const frontFace=mesh(frontTape,geo('plane',()=>new THREE.PlaneGeometry(1,1)),mat.paper,[0,0,1.0],[1,2.8,1],{key:'screen',role:'frontTapeBody'});
  const frontEnds=['a','b'].map(end=>box(frontTape,[1.4,3.2,.4],[0,0,1.35],mat.yellow,{key:'screen',role:'frontTapeEnd',end}));
  let tapeLength=-1,frontLength=-1;
  function replaceScale(mesh,length){
    const previous=mesh.material;if(previous?.userData?.dynamic){previous.map.dispose();textures.delete(previous.map);previous.dispose();materials.delete(previous);printedMaterials.delete(previous);}
    const texture=printedRuler(Math.max(.1,length),Math.min(4096,Math.max(512,Math.ceil(length*28))),192,'#eee9d8',10),value=printedMaterial(texture);value.userData.dynamic=true;mesh.material=value;
  }
  const tapeGroups={};
  function updateTapeStrips(key,items){
    const root=roots[key];let group=tapeGroups[key];if(!group){group=new THREE.Group();root.add(group);tapeGroups[key]=group;}
    while(group.children.length>items.length)group.remove(group.children.at(-1));
    while(group.children.length<items.length){const strip=box(group,[3.2,.045,2],[0,0,0],mat.paper);strip.userData.hit={key,role:'tapeStrip',index:group.children.length-1};}
    items.forEach((point,index)=>{const value=group.children[index];value.position.set(point[0],key==='ruler'?1.28:key==='disk'?3.48:key==='holder'?1.15:.5,-point[1]);});
  }
  const selectBox=new THREE.BoxHelper(ruler,0xc5a3f5);selectBox.visible=false;selectBox.material.transparent=true;selectBox.material.opacity=.78;selectBox.material.depthTest=false;selectBox.renderOrder=100;scene.add(selectBox);geometries.add(selectBox.geometry);materials.add(selectBox.material);
  // Only already-traced segments INSIDE GLASS are drawn. These simple instanced
  // cylinders are a renderer; all refraction/diffraction stays in e1-physics.
  const rayMaterial=new THREE.MeshBasicMaterial({color:'#ff3214',transparent:true,opacity:.96,blending:THREE.NormalBlending,depthWrite:false,toneMapped:false});materials.add(rayMaterial);
  const rays=new THREE.InstancedMesh(geo('rayCylinder',()=>new THREE.CylinderGeometry(1,1,1,5)),rayMaterial,4096);rays.count=0;rays.frustumCulled=false;rays.renderOrder=22;scene.add(rays);
  // Create the instanced shader variant before the student first switches on
  // the laser. Adding instanceColor later otherwise forces an expensive link.
  rays.instanceColor=new THREE.InstancedBufferAttribute(new Float32Array(4096*3).fill(1),3);
  rays.instanceMatrix.setUsage(THREE.DynamicDrawUsage);rays.instanceColor.setUsage(THREE.DynamicDrawUsage);
  const rayOpacity=new THREE.InstancedBufferAttribute(new Float32Array(4096),1);rays.geometry.setAttribute('instanceOpacity',rayOpacity);
  rayOpacity.setUsage(THREE.DynamicDrawUsage);
  rayMaterial.onBeforeCompile=shader=>{
    shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nattribute float instanceOpacity; varying float vRayOpacity;').replace('#include <begin_vertex>','#include <begin_vertex>\nvRayOpacity=instanceOpacity;');
    shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\nvarying float vRayOpacity;').replace('#include <color_fragment>','#include <color_fragment>\ndiffuseColor.a*=vRayOpacity;');
  };
  const spotGeometry=new THREE.BufferGeometry(),spotPositions=new Float32Array(1536),spotBrightness=new Float32Array(512);spotGeometry.setAttribute('position',new THREE.BufferAttribute(spotPositions,3));spotGeometry.setAttribute('brightness',new THREE.BufferAttribute(spotBrightness,1));geometries.add(spotGeometry);
  const spotMaterial=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,uniforms:{pixelScale:{value:400}},vertexShader:`attribute float brightness; varying float v; uniform float pixelScale; void main(){v=brightness;vec4 p=modelViewMatrix*vec4(position,1.);gl_Position=projectionMatrix*p;gl_PointSize=clamp((.45+.65*v)*pixelScale*projectionMatrix[1][1]/max(.1,-p.z),2.5,42.);}`,fragmentShader:`varying float v;void main(){float r=length(gl_PointCoord-vec2(.5))*2.;if(r>1.)discard;float a=exp(-r*r*6.)*(.4+.6*v);gl_FragColor=vec4(vec3(1.,.13,.055)*( .45+.55*v),a);}`});materials.add(spotMaterial);
  const spots=new THREE.Points(spotGeometry,spotMaterial);spots.frustumCulled=false;spots.renderOrder=24;scene.add(spots);
  spotGeometry.setDrawRange(0,0);
  const parchmentMarkers=new THREE.InstancedMesh(geo('contactRing',()=>new THREE.RingGeometry(.13,.20,16)),new THREE.MeshBasicMaterial({color:'#bf7450',side:THREE.DoubleSide,transparent:true,opacity:.8,depthWrite:false}),64);materials.add(parchmentMarkers.material);parchmentMarkers.count=0;parchmentMarkers.frustumCulled=false;scene.add(parchmentMarkers);
  const dummy=new THREE.Object3D(),vector=new THREE.Vector3(),up=new THREE.Vector3(0,1,0),rayColor=new THREE.Color();
  const brightness=(intensity,dark)=>{const value=(options.visibility||options.vis)?.(intensity,dark);return finite(value)?value:clamp(Math.pow(Math.max(0,intensity),.36)*(dark?1:.65),0,1);};
  function pose(key){const result=lab?.pose?.(key);return result||[...(lab?.obj?.[key]?.pos||[0,0]),lab?.obj?.[key]?.ang||0];}
  function redrawProtractor(zero){
    if(protractorZero===zero)return;protractorZero=zero;const previous=protractorMaterial.map;
    protractorMaterial.map=canvasTexture(1024,1024,(c,w,h)=>{
      c.fillStyle='#efefeb';c.fillRect(0,0,w,h);const scale=w/26,cx=w/2,cy=h/2;
      c.textAlign='center';c.textBaseline='middle';c.font='24px Arial, sans-serif';c.fillStyle='#232323';
      for(let degree=0;degree<360;degree+=2){const angle=(degree+zero)*DEG,major=degree%10===0,r=10.9*scale,length=(major?1.05:.55)*scale;c.strokeStyle='#232323';c.lineWidth=major?2.4:1.5;c.beginPath();c.moveTo(cx+Math.cos(angle)*(r-length),cy+Math.sin(angle)*(r-length));c.lineTo(cx+Math.cos(angle)*r,cy+Math.sin(angle)*r);c.stroke();if(major)c.fillText(String(degree),cx+Math.cos(angle)*11.9*scale,cy+Math.sin(angle)*11.9*scale);}
    });protractorMaterial.needsUpdate=true;previous?.dispose();textures.delete(previous);
  }
  function updatePrism(){
    const [cx,cy,a]=pose('holder'),rotation=(a+(lab.hold_rot||0))*DEG,points=lab.prism_poly?.();
    const vertices=points?.length===3?points.map(([x,y])=>{const dx=x-cx,dz=y-cy;return[dx*Math.cos(rotation)-dz*Math.sin(rotation),dx*Math.sin(rotation)+dz*Math.cos(rotation)];}):[0,120,240].map(angle=>[2.9*Math.cos(angle*DEG),-2.9*Math.sin(angle*DEG)]);
    const stamp=vertices.map(p=>p.map(n=>n.toFixed(5)).join(',')).join(';');if(stamp===prismShape)return;prismShape=stamp;
    const top=vertices.map(([x,z])=>[x,8.6,z]),bottom=vertices.map(([x,z])=>[x,3.4,z]),list=[...top[0],...top[1],...top[2],...bottom[0],...bottom[2],...bottom[1]];
    for(let i=0;i<3;i++){const j=(i+1)%3;list.push(...bottom[i],...top[i],...top[j],...bottom[i],...top[j],...bottom[j]);}
    prismGeometry.attributes.position.array.set(list);prismGeometry.attributes.position.needsUpdate=true;prismGeometry.computeVertexNormals();prismGeometry.computeBoundingSphere();
    const wrapped=vertices.map(([x,z])=>{const scale=1+.018/Math.max(.001,Math.hypot(x,z));return[x*scale,z*scale];});
    const lower=wrapped.map(([x,z])=>[x,3.4,z]),upper=wrapped.map(([x,z])=>[x,4.8,z]),band=[];
    for(let i=0;i<3;i++){const j=(i+1)%3;band.push(...lower[i],...lower[j],...upper[j],...lower[i],...upper[j],...upper[i]);}
    prismBandGeometry.attributes.position.array.set(band);prismBandGeometry.attributes.position.needsUpdate=true;prismBandGeometry.computeVertexNormals();prismBandGeometry.computeBoundingSphere();
  }
  function updateRays(trace){
    let rayCount=0,spotCount=0,markerCount=0;const height=lab.level==='high'?HIGH:LOW;
    const addSpot=(x,y,z,intensity)=>{if(spotCount>=512||intensity<=.02)return;spotPositions.set([x,y,z],spotCount*3);spotBrightness[spotCount++]=intensity;};
    for(const segment of trace?.segments||trace?.segs||[]){
      if(segment[5]!=='glass')continue;
      const [x0,z0,x1,z1,intensity]=segment,parts=lab.obj?.ruler8?.on?12:1,dx=(x1-x0)/parts,dz=(z1-z0)/parts,length=Math.hypot(dx,dz);if(!length)continue;
      for(let i=0;i<parts&&rayCount<4096;i++){
        const x=x0+(i+.5)*dx,z=z0+(i+.5)*dz,under=lab.in_ruler8?.(x,z),v=brightness(intensity*.60,lab.dark)*(under ? .58 : 1);if(v<=.02)continue;
        const shift=under ? .16 : 0;dummy.position.set(x-dz/length*shift,height,z+dx/length*shift);dummy.quaternion.setFromUnitVectors(up,vector.set(dx,0,dz).normalize());dummy.scale.set(.045+.035*v,length,.045+.035*v);dummy.updateMatrix();rays.setMatrixAt(rayCount,dummy.matrix);rayColor.setRGB(1,1,1);rays.setColorAt(rayCount,rayColor);rayOpacity.setX(rayCount++,v);
      }
    }
    for(const [x,z,intensity] of trace?.spots||[]){let xx=x,zz=z;if(Math.abs(x)<.15)xx=.08;if(Math.abs(x-ROOM_W)<.15)xx=ROOM_W-.08;if(Math.abs(z)<.15)zz=.08;if(Math.abs(z-ROOM_D)<.15)zz=ROOM_D-.08;addSpot(xx,height,zz,brightness(intensity*(lab.in_ruler8?.(x,z) ? .58 : 1),lab.dark));}
    if(lab.obj?.screen?.on){const [x,z,a]=pose('screen'),rotation=a*DEG;for(const [offset,intensity] of trace?.shots||[]){const nx=Math.sin(rotation),nz=Math.cos(rotation),laser=lab.laser?.()||[136,170],side=(laser[0]-x)*nx+(laser[1]-z)*nz>=0?1:-1;addSpot(x+offset*Math.cos(rotation)+nx*.86*side,height,z-offset*Math.sin(rotation)+nz*.86*side,brightness(intensity,lab.dark));}}
    if(lab.parchment&&lab.obj?.disk?.on){const [cx,cz]=pose('disk');for(const point of trace?.hits||[]){if(markerCount>=64)break;dummy.position.set(point[0],height,point[1]);dummy.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),vector.set(point[0]-cx,0,point[1]-cz).normalize());dummy.scale.setScalar(1);dummy.updateMatrix();parchmentMarkers.setMatrixAt(markerCount++,dummy.matrix);}}
    rays.count=rayCount;rays.instanceMatrix.needsUpdate=true;rayOpacity.needsUpdate=true;if(rays.instanceColor)rays.instanceColor.needsUpdate=true;
    spotGeometry.setDrawRange(0,spotCount);spotGeometry.attributes.position.needsUpdate=true;spotGeometry.attributes.brightness.needsUpdate=true;
    parchmentMarkers.count=markerCount;parchmentMarkers.instanceMatrix.needsUpdate=true;
  }
  function update(nextLab,trace){
    if(disposed||!nextLab)return;lab=nextLab;lastTrace=trace;
    for(const [key,group] of Object.entries(roots)){group.visible=!!lab.obj?.[key]?.on;const [x,z,a]=pose(key);group.position.set(x,0,z);group.rotation.y=a*DEG;updateTapeStrips(key,lab.obj?.[key]?.tapes||[]);}
    // The original stacking order lets the clear 30 cm rule rest on the disk.
    // Raise only the actual overlapping rule, rather than floating it in air.
    if(lab.obj?.ruler8?.on&&lab.obj?.disk?.on&&(lab.order||[]).indexOf('ruler8')>(lab.order||[]).indexOf('disk')){
      const [rx,rz,ra]=pose('ruler8'),[dx,dz,da]=pose('disk'),r=ra*DEG,d=da*DEG,offset=[dx-rx,dz-rz],u=[Math.cos(r),-Math.sin(r)],v=[-Math.sin(r),-Math.cos(r)],du=[Math.cos(d),-Math.sin(d)],dv=[-Math.sin(d),-Math.cos(d)];
      const localX=offset[0]*u[0]+offset[1]*u[1],localZ=offset[0]*v[0]+offset[1]*v[1],closeX=clamp(localX,-15.6,15.6),closeZ=clamp(localZ,-1.9,1.9),onGlass=(localX-closeX)**2+(localZ-closeZ)**2<100;
      const dot=(a,b)=>a[0]*b[0]+a[1]*b[1],onBoard=[u,v,du,dv].every(axis=>Math.abs(dot(offset,axis))<=15.6*Math.abs(dot(u,axis))+1.9*Math.abs(dot(v,axis))+15.2*(Math.abs(dot(du,axis))+Math.abs(dot(dv,axis))));
      ruler8.position.y=onGlass?3.36:onBoard ? .96 : 0;
    }
    slider.position.x=lab.slider||0;head.rotation.y=(lab.laser_fine||0)*DEG;diodeAssembly.position.y=lab.level==='high'?HIGH:LOW;
    diodeSupport.scale.y=lab.level==='high'?5.2:1;diodeSupport.position.y=lab.level==='high'?3.9:1.9;
    lowRedLead.visible=lowBlackLead.visible=lab.level!=='high';highRedLead.visible=highBlackLead.visible=lab.level==='high';
    fineBar.position.y=lab.level==='high'?HIGH:LOW;switchTip.rotation.z=lab.laser_on?-.28:.28;apertureMaterial.color.set(lab.laser_on?'#ff3214':'#421811');
    turning.rotation.y=(lab.hold_rot||0)*DEG;grating.visible=lab.hold_item!=='prism';prism.visible=lab.hold_item==='prism';prismBand.visible=prism.visible;updatePrism();
    parchment.visible=!!lab.parchment;redrawProtractor(Number(lab.prot_zero)||0);
    tape.visible=!!lab.tape_on;
    if(tape.visible){const a=lab.tape_a||[50,192],b=lab.tape_b||[170,192],dx=b[0]-a[0],dz=b[1]-a[1],length=Math.max(.01,Math.hypot(dx,dz));tape.position.set(a[0],0,a[1]);tape.rotation.y=-Math.atan2(dz,dx);tapeFace.position.x=length/2;tapeFace.scale.x=length;tapeEnd.position.x=length;if(Math.abs(tapeLength-length)>.02){replaceScale(tapeFace,length);tapeLength=length;}}
    frontTape.visible=viewMode==='screen'&&!!lab.obj?.screen?.on;
    if(frontTape.visible){const a=lab.ftape_a||[-40,6],b=lab.ftape_b||[40,6],dx=b[0]-a[0],dy=b[1]-a[1],length=Math.max(.01,Math.hypot(dx,dy)),height=lab.level==='high'?HIGH:LOW;frontFace.position.set((a[0]+b[0])/2,height-(a[1]+b[1])/2,1.02);frontFace.scale.x=length;frontFace.rotation.z=-Math.atan2(dy,dx);for(let i=0;i<2;i++){const p=i?b:a;frontEnds[i].position.set(p[0],height-p[1],1.35);}if(Math.abs(frontLength-length)>.02){replaceScale(frontFace,length);frontLength=length;}}
    if(lastDark!==!!lab.dark){lastDark=!!lab.dark;ambient.intensity=lab.dark ? .14 : 1.35;keyLight.intensity=lab.dark ? .11 : 1.85;scene.background.set(lab.dark?'#090d0b':'#26352f');matMaterial.color.set(lab.dark?'#43604c':'#ffffff');wallMaterial.color.set(lab.dark?'#4f5148':'#e9e2d2');}
    lampLight.intensity=lab.lamp?45000:0;bulbMaterial.emissiveIntensity=lab.lamp?1.4:0;
    for(const value of printedMaterials)value.color.set(lab.dark?(lab.lamp?'#bbb6a2':'#242a26'):'#ffffff');
    updateRays(trace);refreshSelection();invalidate();
    if(!warmed&&renderer.compileAsync){warmed=true;renderer.compileAsync(scene,camera).then(()=>{if(!disposed)invalidate();}).catch(()=>{});}
  }
  function refreshSelection(){
    const key=selectedKey==='laser'?'ruler':selectedKey==='holder12b'?'holder':selectedKey,group=selectedKey==='laser'?head:selectedKey==='holder12b'?turning:roots[key]||null;
    selectBox.visible=!!group&&!!roots[key]?.visible;if(selectBox.visible){group.updateWorldMatrix(true,true);selectBox.setFromObject(group);}
  }
  function selected(key){selectedKey=key||null;refreshSelection();invalidate();}
  function render(){frame=0;if(disposed)return;controls.update();renderer.render(scene,camera);}
  function invalidate(){if(!disposed&&!frame)frame=requestAnimationFrame(render);}
  controls.addEventListener('change',invalidate);
  function resize(){
    if(disposed)return;const width=Math.max(1,container.clientWidth),height=Math.max(1,container.clientHeight||520);camera.aspect=width/height;
    if(initialFit&&container.clientWidth>0){const factor=Math.max(1,1.1/camera.aspect);camera.position.sub(controls.target).multiplyScalar(factor).add(controls.target);initialFit=false;}
    camera.updateProjectionMatrix();renderer.setSize(width,height,false);spotMaterial.uniforms.pixelScale.value=height*.5*renderer.getPixelRatio();invalidate();
  }
  const observer=typeof ResizeObserver==='function'?new ResizeObserver(resize):null;observer?.observe(container);
  function focus(key){
    if(!lab)return;const actual=key==='laser'?'ruler':key==='holder12b'?'holder':key,[x,z]=pose(actual),target=new THREE.Vector3(x,key==='laser'?3:1.5,z),distance=({disk:43,ruler:80,laser:24,holder:32,holder12b:24,ruler8:42,screen:145,tape6:20})[key]||85;
    if(key==='laser'){const p=lab.pivot?.();if(p)target.set(p[0],3,p[1]);}
    const offset=camera.position.clone().sub(controls.target).normalize();if(viewMode==='top')offset.set(0,1,.0001);camera.position.copy(target).addScaledVector(offset,distance);controls.target.copy(target);controls.update();invalidate();
  }
  function setView(view){
    viewMode=['top','screen'].includes(view)?view:'perspective';controls.enableRotate=viewMode==='perspective';
    if(viewMode==='screen'&&lab?.obj?.screen?.on){const [x,z,a]=pose('screen'),normal=new THREE.Vector3(Math.sin(a*DEG),0,Math.cos(a*DEG)),laser=lab.laser?.()||[136,170];if((laser[0]-x)*normal.x+(laser[1]-z)*normal.z<0)normal.negate();const distance=Math.max(65,120/(2*Math.tan(camera.fov*DEG/2)*camera.aspect)*1.08);controls.target.set(x,lab.level==='high'?HIGH:LOW,z);camera.position.copy(controls.target).addScaledVector(normal,distance);camera.position.y+=.04;}
    else if(viewMode==='top'){const target=controls.target.clone(),distance=Math.max(43,camera.position.distanceTo(target));camera.position.copy(target).add(new THREE.Vector3(0,distance,.001));}
    else{const target=controls.target.clone(),distance=Math.max(60,camera.position.distanceTo(target));camera.position.copy(target).add(new THREE.Vector3(.23,.68,.70).normalize().multiplyScalar(distance));}
    if(lab)update(lab,lastTrace);controls.update();invalidate();
  }
  function hitAt(event){const rect=canvas.getBoundingClientRect();pointer.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);ray.setFromCamera(pointer,camera);return ray.intersectObjects(pickables,true).find(hit=>{let node=hit.object;while(node){if(!node.visible)return false;node=node.parent;}return true;})||null;}
  function hitMeta(hit){let object=hit?.object;while(object){if(object.userData.hit)return object.userData.hit;object=object.parent;}return null;}
  function planeAt(event){hitAt(event);return ray.ray.intersectPlane(ground,groundPoint)?.clone()||null;}
  const actualKey=key=>key==='laser'?'ruler':key==='holder12b'?'holder':key;
  function pointerDown(event){
    if(disposed||!lab)return;dragPointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
    if(event.pointerType==='touch'&&dragPointers.size===2){action=null;controls.enabled=false;const points=[...dragPointers.values()];gesture={distance:Math.hypot(points[0].x-points[1].x,points[0].y-points[1].y),mid:[(points[0].x+points[1].x)/2,(points[0].y+points[1].y)/2],position:camera.position.clone(),target:controls.target.clone()};event.stopImmediatePropagation();return;}
    const hit=hitAt(event),meta=hitMeta(hit),point=planeAt(event);if(!meta){options.onSelect?.(null);selected(null);if(lab.tape_held)options.onTapeHeld?.(false);return;}
    if(viewMode==='screen'&&meta.role!=='frontTapeEnd'){options.onSelect?.(meta.key);selected(meta.key);return;}
    if(meta.key!=='tape6')options.onSelect?.(meta.key);selected(meta.key);canvas.focus({preventScroll:true});controls.enabled=false;canvas.setPointerCapture(event.pointerId);event.stopImmediatePropagation();event.preventDefault();
    const key=actualKey(meta.key),position=lab.obj?.[key]?.pos||[0,0];
    action={meta,key,point,start:[event.clientX,event.clientY],previous:[event.clientX,event.clientY],position:[...position],moved:false,rotate:event.shiftKey||event.button===2,angle:point?Math.atan2(point.z-position[1],point.x-position[0]):0};
  }
  function pointerMove(event){
    if(dragPointers.has(event.pointerId))dragPointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
    if(gesture&&dragPointers.size>=2){const points=[...dragPointers.values()],distance=Math.max(1,Math.hypot(points[0].x-points[1].x,points[0].y-points[1].y)),mid=[(points[0].x+points[1].x)/2,(points[0].y+points[1].y)/2],ratio=clamp(gesture.distance/distance,.15,6),offset=gesture.position.clone().sub(gesture.target).multiplyScalar(ratio),scale=gesture.position.distanceTo(gesture.target)*.0015,right=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,0);right.y=0;right.normalize();const forward=new THREE.Vector3().crossVectors(up,right).normalize(),delta=right.multiplyScalar((gesture.mid[0]-mid[0])*scale).addScaledVector(forward,(mid[1]-gesture.mid[1])*scale);controls.target.copy(gesture.target).add(delta);camera.position.copy(controls.target).add(offset);controls.update();invalidate();event.stopImmediatePropagation();return;}
    if(!action)return;event.stopImmediatePropagation();const a=action,meta=a.meta,point=planeAt(event),dx=event.clientX-a.previous[0];
    a.moved||=Math.hypot(event.clientX-a.start[0],event.clientY-a.start[1])>4;if(!a.moved)return;
    if(meta.role==='frontTapeEnd'){
      screen.updateWorldMatrix(true,false);const normal=new THREE.Vector3(0,0,1).transformDirection(screen.matrixWorld),plane=new THREE.Plane().setFromNormalAndCoplanarPoint(normal,screen.localToWorld(new THREE.Vector3(0,0,1.35))),q=ray.ray.intersectPlane(plane,new THREE.Vector3());if(q){screen.worldToLocal(q);options.onFrontTapeMove?.(meta.end,[q.x,(lab.level==='high'?HIGH:LOW)-q.y]);}
    }else if(meta.role==='tapeEnd'&&point)options.onTapeMove?.(meta.end,[clamp(point.x,0,ROOM_W),clamp(point.z,0,ROOM_D)]);
    else if(a.rotate||meta.role==='fine'){
      let delta=dx*(event.shiftKey?.125:.5);if(point&&Math.hypot(point.x-a.position[0],point.z-a.position[1])>4){const angle=Math.atan2(point.z-a.position[1],point.x-a.position[0]);delta=THREE.MathUtils.radToDeg(a.angle-angle);if(delta>180)delta-=360;if(delta< -180)delta+=360;a.angle=angle;}
      if(meta.role==='holderRotate')options.onHolderRotate?.(delta);else if(meta.role==='fine'||meta.key==='laser')options.onFineRotate?.(delta);else options.onRotate?.(a.key,delta);
    }else if(meta.key==='laser'&&point){const [x,z,angle]=pose('ruler'),r=angle*DEG;options.onSlider?.((point.x-x)*Math.cos(r)-(point.z-z)*Math.sin(r));}
    else if(point&&a.point&&a.key!=='tape'&&meta.role!=='tapeStrip')options.onMove?.(a.key,[a.position[0]+point.x-a.point.x,a.position[1]+point.z-a.point.z]);
    a.previous=[event.clientX,event.clientY];
  }
  function pointerUp(event){
    dragPointers.delete(event.pointerId);if(gesture){if(dragPointers.size<2){gesture=null;controls.enabled=true;}return;}
    if(!action)return;const a=action;action=null;controls.enabled=true;event.stopImmediatePropagation();
    if(!a.moved){const point=planeAt(event);if(a.meta.role==='tapeStrip')options.onTapePeel?.(a.key,a.meta.index);
      else if(a.key==='tape6')options.onTapeHeld?.(!lab.tape_held);
      else if(lab.tape_held&&lab.obj?.tape6?.on&&point)options.onTapeStick?.(a.key,[point.x,point.z]);
      else if(a.meta.role==='switch')options.onSwitch?.(!lab.laser_on);
    }
    invalidate();
  }
  function wheel(event){
    if(!event.shiftKey||!lab)return;const meta=hitMeta(hitAt(event));if(!meta)return;event.preventDefault();event.stopImmediatePropagation();const delta=event.deltaY<0?.25:-.25;if(meta.role==='holderRotate')options.onHolderRotate?.(delta);else if(meta.key==='laser')options.onFineRotate?.(delta);else options.onRotate?.(actualKey(meta.key),delta);
  }
  function keyDown(event){
    if(!lab||!selectedKey)return;const key=actualKey(selectedKey),step=event.shiftKey?.1:.5,position=lab.obj?.[key]?.pos;
    if(position&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();const dx=event.key==='ArrowLeft'?-step:event.key==='ArrowRight'?step:0,dz=event.key==='ArrowUp'?-step:event.key==='ArrowDown'?step:0;options.onMove?.(key,[position[0]+dx,position[1]+dz]);}
    else if(event.key==='['||event.key===']'){event.preventDefault();const delta=(event.key===']'?1:-1)*(event.shiftKey?.25:2);if(selectedKey==='holder12b')options.onHolderRotate?.(delta);else if(selectedKey==='laser')options.onFineRotate?.(delta);else options.onRotate?.(key,delta);}
    else if(event.code==='Space'&&key==='ruler'){event.preventDefault();options.onSwitch?.(!lab.laser_on);}
  }
  function pointerCancel(event){dragPointers.delete(event.pointerId);action=null;if(dragPointers.size<2)gesture=null;controls.enabled=true;}
  const listeners=[['pointerdown',pointerDown,true],['pointermove',pointerMove,true],['pointerup',pointerUp,true],['pointercancel',pointerCancel,true],['wheel',wheel,{capture:true,passive:false}],['keydown',keyDown,false],['contextmenu',event=>event.preventDefault(),false]];
  for(const [name,handler,capture]of listeners)canvas.addEventListener(name,handler,capture);
  function dispose(){
    if(disposed)return;disposed=true;cancelAnimationFrame(frame);observer?.disconnect();controls.dispose();for(const [name,handler,capture]of listeners)canvas.removeEventListener(name,handler,capture);
    for(const value of geometries)value.dispose();for(const value of materials)value.dispose();for(const value of textures)value.dispose();renderer.dispose();canvas.remove();
  }
  resize();controls.update();invalidate();
  return{update,setView,selected,focus,resize,dispose,canvas};
}
