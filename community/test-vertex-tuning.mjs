// node --test community/test-vertex-tuning.mjs
// Vertex AI tuning from the Worker: the service account's signed JWT for a token, uploads to the bucket, the tuning job.
import assert from "node:assert/strict";
import test from "node:test";
import { gcpConfig, gcpToken, gcsPut, startTuning, tuningStatus, cancelTuning } from "./src/vertex-tuning.js";

async function serviceAccount() {
  const kp = await crypto.subtle.generateKey({ name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" }, true, ["sign", "verify"]);
  const der = new Uint8Array(await crypto.subtle.exportKey("pkcs8", kp.privateKey));
  const pem = "-----BEGIN PRIVATE KEY-----\n" + Buffer.from(der).toString("base64").match(/.{1,64}/g).join("\n") + "\n-----END PRIVATE KEY-----\n";
  return { kp, json: JSON.stringify({ type: "service_account", project_id: "proj-1", client_email: "tuner@proj-1.iam.gserviceaccount.com", private_key: pem }) };
}

test("the service account signs a JWT for a cloud-platform token; config reports names, never values", async () => {
  const { kp, json } = await serviceAccount();
  const env = { GCP_SA_KEY: json, GCP_TUNING_BUCKET: "gs://haslalab-tuning/" };
  const cfg = gcpConfig(env); assert.equal(cfg.project, "proj-1", "the key's project when GCP_PROJECT is unset"); assert.equal(cfg.bucket, "haslalab-tuning");
  assert.deepEqual(cfg.present, { GCP_SA_KEY: true, sa_key_valid: true, GCP_PROJECT: false, GCP_TUNING_BUCKET: true });
  let form;
  const token = await gcpToken(env, { now: 1_800_000_000_000, fetchImpl: async (url, init) => { assert.equal(url, "https://oauth2.googleapis.com/token"); form = new URLSearchParams(init.body); return Response.json({ access_token: "ya29.x" }); } });
  assert.equal(token, "ya29.x"); assert.equal(form.get("grant_type"), "urn:ietf:params:oauth:grant-type:jwt-bearer");
  const [h, c, sig] = form.get("assertion").split("."), dec = s => JSON.parse(Buffer.from(s, "base64url").toString());
  assert.deepEqual(dec(h), { alg: "RS256", typ: "JWT" });
  assert.equal(dec(c).iss, "tuner@proj-1.iam.gserviceaccount.com"); assert.equal(dec(c).scope, "https://www.googleapis.com/auth/cloud-platform"); assert.equal(dec(c).exp - dec(c).iat, 3600);
  assert.ok(await crypto.subtle.verify("RSASSA-PKCS1-v1_5", kp.publicKey, Buffer.from(sig, "base64url"), new TextEncoder().encode(h + "." + c)), "a valid RS256 signature");
  await assert.rejects(gcpToken({ GCP_SA_KEY: "{not json" }), /gcp_sa_key_missing/);
});

test("uploads go to the tuning bucket; a tuning job is created over the JSONL and its state read back", async () => {
  const env = { GCP_SA_KEY: JSON.stringify({ client_email: "a@b", private_key: "x", project_id: "proj-1" }), GCP_TUNING_BUCKET: "gs://bk", GCP_REGION: "us-central1" };
  const seen = [];
  const fetchImpl = async (url, init) => { seen.push({ url, init }); return url.includes("/tuningJobs/") ? Response.json({ name: "projects/proj-1/locations/us-central1/tuningJobs/77", state: "JOB_STATE_SUCCEEDED", tunedModel: { endpoint: "projects/proj-1/locations/us-central1/endpoints/9" } })
    : url.includes("tuningJobs") ? Response.json({ name: "projects/proj-1/locations/us-central1/tuningJobs/77", state: "JOB_STATE_PENDING" }) : Response.json({ name: "lab-pages/1.jpg" }); };
  const uri = await gcsPut(env, "tok", "lab-pages/1.jpg", new Uint8Array([1, 2]), "image/jpeg", { fetchImpl });
  assert.equal(uri, "gs://bk/lab-pages/1.jpg");
  assert.equal(seen[0].url, "https://storage.googleapis.com/upload/storage/v1/b/bk/o?uploadType=media&name=lab-pages%2F1.jpg"); assert.equal(seen[0].init.headers.Authorization, "Bearer tok");
  const job = await startTuning(env, "tok", { baseModel: "gemini-3.1-flash-lite", train: "gs://bk/runs/1/train.jsonl", validation: "gs://bk/runs/1/validation.jsonl", epochs: 4, fetchImpl });
  assert.equal(seen[1].url, "https://us-central1-aiplatform.googleapis.com/v1/projects/proj-1/locations/us-central1/tuningJobs");
  const body = JSON.parse(seen[1].init.body);
  assert.equal(body.baseModel, "gemini-3.1-flash-lite"); assert.equal(body.supervisedTuningSpec.trainingDatasetUri, "gs://bk/runs/1/train.jsonl"); assert.equal(body.supervisedTuningSpec.hyperParameters.epochCount, 4);
  assert.equal(job.state, "JOB_STATE_PENDING");
  const st = await tuningStatus(env, "tok", job.job, { fetchImpl });
  assert.equal(st.state, "JOB_STATE_SUCCEEDED"); assert.equal(st.endpoint, "projects/proj-1/locations/us-central1/endpoints/9");
  await assert.rejects(tuningStatus(env, "tok", "../x", { fetchImpl }), /bad_job/);
});

test("a tuning job is cancelled with POST :cancel on its own name; a bad name is refused before any call", async () => {
  const calls = [], env = { GCP_PROJECT: "proj-1", GCP_REGION: "us-central1" };
  const fetchImpl = async (url, init) => { calls.push({ url, init }); return new Response("{}", { status: 200 }); };
  const job = "projects/315/locations/us-central1/tuningJobs/1258";
  assert.deepEqual(await cancelTuning(env, "tok", job, { fetchImpl }), { job, cancelled: true });
  assert.equal(calls[0].url, "https://us-central1-aiplatform.googleapis.com/v1/" + job + ":cancel");
  assert.equal(calls[0].init.method, "POST");
  await assert.rejects(cancelTuning(env, "tok", job + "/../x", { fetchImpl }), /bad_job/);
  assert.equal(calls.length, 1);
  await assert.rejects(cancelTuning(env, "tok", job, { fetchImpl: async () => new Response('{"error":{"message":"no"}}', { status: 400 }) }), /tuning_cancel_400/);
});
