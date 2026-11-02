// Private subprocess bridge for Python preparation. Only thin question envelopes
// (identity, versions and context; no image bytes) travel over captured stdio.
import {applyContextTextOverlays,readContextTextOverlays} from './store.mjs';
try{
  let input='';for await(const chunk of process.stdin)input+=chunk;
  const {manifest,questions,overlay_path}=JSON.parse(input);
  const overlay=await readContextTextOverlays(overlay_path);
  process.stdout.write(JSON.stringify(applyContextTextOverlays(manifest,questions,overlay)));
}catch(error){console.error(error.message);process.exitCode=1;}
