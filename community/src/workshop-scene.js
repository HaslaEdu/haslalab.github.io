/* Photo → figure (#/workshop/draw, "문제 사진으로 시작"): POST /api/workshop/scene-from-image
   A member sends one photo of a mechanics problem ({image: data URL (JPEG, PNG or WebP, at most SCENE_IMAGE_BYTES),
   lang}). The selected vision model (vision-provider.js visionJSON, the provider practice-grade.js uses) is asked for
   the figure as a scene of the editor's schema only (draw-scene.mjs, shared with the browser), mechanics only. The
   answer is checked by the same validateScene() the editor uses, leniently: an object with a problem is dropped and
   reported, a number out of range is brought into range and reported, labels must look like physics labels. The raw
   model text never goes back: the reply is the validated scene and a list of {id, what} the model or the check was
   unsure of (`what` one of UNSURE_FIELDS, so the page words it itself). The photo is not stored.
   Limits: needUser; SCENE_DAILY a day per member (kind 'scene' in ai_usage_daily, given back when the failure is on
   our side), SCENE_FLOOD a minute; a photo that does not show mechanics still counts. */
import { visionJSON } from './vision-provider.js';
import { gradeProvider } from './practice-grade.js';
import { takeOne, giveBack, utcDay, ensureLearnSchema } from './learn-services.js';
import { validateScene, VISION_OBJECT_TYPES, UNSURE_FIELDS, MAX_OBJECTS } from '../../draw-scene.mjs';

export const SCENE_PATH = '/api/workshop/scene-from-image';
export const SCENE_DAILY = 20, SCENE_FLOOD = 4, SCENE_IMAGE_BYTES = 4 * 1024 * 1024;
const MAGIC = {'image/jpeg': b => b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff,
  'image/png': b => b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47,
  'image/webp': b => String.fromCharCode(b[0], b[1], b[2], b[3]) === 'RIFF' && String.fromCharCode(b[8], b[9], b[10], b[11]) === 'WEBP'};

/** a photo as a data URL of a real JPEG, PNG or WebP of at most SCENE_IMAGE_BYTES: {mime, data} or null */
export function cleanImage(v) {
  const m = typeof v === 'string' && v.length < SCENE_IMAGE_BYTES * 1.4 && /^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/]+={0,2})$/.exec(v);
  if (!m || m[2].length % 4) return null;
  const bytes = m[2].length * 3 / 4 - (m[2].endsWith('==') ? 2 : m[2].endsWith('=') ? 1 : 0);
  if (bytes < 100) return null;
  if (bytes > SCENE_IMAGE_BYTES) return 'too_large';
  let head;
  try { head = Uint8Array.from(atob(m[2].slice(0, 16)), c => c.charCodeAt(0)); } catch { return null; }
  return MAGIC[m[1]](head) ? {mime: m[1], data: m[2], label: '[The photographed problem]'} : null;
}

const N = {type: 'number'}, S = {type: 'string'}, B = {type: 'boolean'};
export const SCENE_RESPONSE = {type: 'object', properties: {
  mechanics: B,
  g: N,
  objects: {type: 'array', items: {type: 'object', properties: {
    id: S, type: {type: 'string', enum: VISION_OBJECT_TYPES},
    x: N, y: N, w: N, h: N, r: N, mass: N, label: S, on: S, at: N, vx: N, vy: N,
    angle: N, length: N, mu: N, flip: B, angleLabel: S, side: {type: 'string', enum: ['left', 'right']}, mount: S,
    a: S, b: S, over: {type: 'array', items: S}, mode: {type: 'string', enum: ['normal', 'conical']},
    k: N, L0: N, F: N, text: S, from: N, to: N
  }, required: ['id', 'type']}},
  unsure: {type: 'array', items: {type: 'object', properties: {id: S, what: {type: 'string', enum: UNSURE_FIELDS}}, required: ['what']}}
}, required: ['mechanics', 'objects', 'unsure']};

export const scenePolicy = () => `You turn the figure of a photographed physics problem into a scene for a figure editor. Mechanics only.
If the photo does not show a mechanics problem (blocks, balls, inclines, floors, walls, pulleys, strings, springs, pendulums, projectiles, applied forces), answer {"mechanics":false,"objects":[],"unsure":[]}.
Otherwise describe what the figure shows, as objects. Units: metres, kg, N, degrees. y points up; put the floor at y = 0 and the figure between x = 0 and x = 4 when no size is given.
Types and fields (anything else is ignored):
- floor {x,y,w,mu}: the top surface from (x,y) to (x+w,y). ceiling {x,y,w}. wall {x,y,h,side:'left'|'right' (the solid side)}.
- incline {x,y,angle,length,mu,flip,angleLabel}: the slope rises to the right from its foot (x,y), length along the slope; flip:true rises to the left. angleLabel like "\\theta" or "30°".
- block {id,x,y,w,h,mass,label}: x,y its centre. A block resting on a floor or incline: give on (that surface's id) and at (distance along the surface from its start to the block), not x,y.
- ball {x,y,r,mass,label,vx,vy}: vx,vy the initial velocity if the problem gives one.
- pulley {x,y,r,mount}: fixed; mount the id of the ceiling/incline/floor/wall it is fixed to.
- pivot {x,y}: a fixed point a pendulum hangs from.
- string {a,b,over,mode}: a and b are bodies or a pivot; over the pulley ids in order from a to b. A hanging body must be directly below its pulley's left or right edge. mode 'conical' for a conical pendulum.
- rod {a: pivot, b: body}. spring {a,b,k,L0}: ends are bodies, walls, ceilings, floors or pivots.
- force {on,F,angle,label}: a constant applied force on a body, angle from +x anticlockwise.
- label {x,y,text} for a letter in the figure. arc {x,y,r,from,to,text} for a marked angle.
Use the values written in the problem (masses, angles, friction coefficients, spring constants, speeds). When a value is not given, choose a plausible one and list it in unsure.
Labels: short, like m_1, M, \\theta, \\mu, v_0, F, k. ids: short letters and digits (m1, p1, s1). At most ${MAX_OBJECTS} objects.
unsure: every object or value you guessed or could not read, as {"id": the object's id, "what": one of ${UNSURE_FIELDS.join(', ')}}.
Return only the JSON object.`;

/** the model's answer → {scene, unsure}; null when it is not a usable mechanics figure */
export function sceneFromAnswer(raw) {
  if (!raw || typeof raw !== 'object' || raw.mechanics === false || !Array.isArray(raw.objects) || !raw.objects.length) return null;
  const objects = raw.objects.slice(0, MAX_OBJECTS).filter(o => o && typeof o === 'object' && VISION_OBJECT_TYPES.includes(o.type))
    .map(o => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== null && v !== '')));
  const r = validateScene({g: typeof raw.g === 'number' ? raw.g : 9.8, objects}, {lenient: true, aiText: true});
  if (!r.scene.objects.length) return null;
  const ids = new Set(r.scene.objects.map(o => o.id)), unsure = [], seen = new Set();
  const add = (id, what) => { const k = (id || '') + ':' + what; if (seen.has(k) || unsure.length >= 30) return; seen.add(k); unsure.push(id ? {id, what} : {what}); };
  for (const u of Array.isArray(raw.unsure) ? raw.unsure : []) if (u && UNSURE_FIELDS.includes(u.what)) add(typeof u.id === 'string' && ids.has(u.id) ? u.id : '', u.what);
  const FIELD_WHAT = {mass: 'mass', angle: 'angle', mu: 'mu', k: 'k', L0: 'length', length: 'length', vx: 'velocity', vy: 'velocity', F: 'force', label: 'label', text: 'label', angleLabel: 'label', x: 'position', y: 'position', at: 'position'};
  for (const n of r.notes) {
    if (n.code === 'dropped' || n.code === 'too_many') add('', 'object');
    else if (n.id && ids.has(n.id)) add(n.id, n.code === 'ref_dropped' ? 'connection' : FIELD_WHAT[n.field] || 'value');
  }
  if (r.errors.some(e => e.id && !ids.has(e.id)) || objects.length < raw.objects.length) add('', 'object');
  return {scene: r.scene, unsure};
}

const readScene = (env, {provider, image, lang}) => visionJSON(env, {provider, stage: 'scene', policy: scenePolicy(),
  input: {task: 'figure_to_scene', language_of_labels: lang === 'en' ? 'English' : 'Korean'}, images: [image], schema: SCENE_RESPONSE, maxTokens: 6144, timeoutMs: 60000});

export function createWorkshopSceneRouter({HttpError, needUser, limit, now, bad, vision = readScene}) {
  return async function workshopSceneRoute(p, m, body, me, req, env) {
    if (p !== SCENE_PATH) return undefined;
    if (m !== 'POST') throw new HttpError(405, 'method_not_allowed');
    needUser(me);
    const image = cleanImage(body?.image);
    if (image === 'too_large') throw new HttpError(413, 'image_too_large');
    if (!image) bad('bad_image');
    const lang = body?.lang === 'en' ? 'en' : 'ko';
    const provider = gradeProvider(env);
    if (!provider) throw new HttpError(503, 'ai_unavailable');
    await limit(env, 'scene-flood:' + me.id, SCENE_FLOOD, 60);
    await ensureLearnSchema(env);
    const day = utcDay(now()), used = await takeOne(env, me.id, 'scene', day, SCENE_DAILY);
    if (used == null) throw new HttpError(429, 'scene_limit');
    let raw;
    try { raw = (await vision(env, {provider, image, lang}))?.raw; }
    catch (e) { await giveBack(env, me.id, 'scene', day); throw new HttpError(503, e?.code === 'provider_unavailable' ? 'ai_unavailable' : 'scene_failed'); }
    if (!raw || typeof raw !== 'object') { await giveBack(env, me.id, 'scene', day); throw new HttpError(503, 'scene_failed'); }
    const out = sceneFromAnswer(raw);
    if (!out) throw new HttpError(422, raw.mechanics === false ? 'not_mechanics' : 'no_figure');
    return {scene: out.scene, unsure: out.unsure, left: Math.max(0, SCENE_DAILY - used)};
  };
}
