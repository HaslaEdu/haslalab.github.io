// node --test community/test-page-tiles.mjs
// Image tiling for the page reader: overlapping zoomed strips of a JPEG page; anything else gets none.
import assert from "node:assert/strict";
import test from "node:test";
import jpeg from "jpeg-js";
import { pageStrips, cropJpeg } from "./src/page-tiles.js";

const page = (width, height) => {
  const data = new Uint8Array(width * height * 4);
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) { const i = (y * width + x) * 4; data[i] = data[i + 1] = data[i + 2] = y < height / 2 ? 30 : 220; data[i + 3] = 255; }
  return new Uint8Array(jpeg.encode({ width, height, data }, 90).data);
};
test("a page becomes overlapping strips from top to bottom, each a JPEG of the full width", () => {
  const strips = pageStrips(page(200, 400), 2, 0.1);
  assert.equal(strips.length, 2);
  const [top, bottom] = strips.map(s => jpeg.decode(s, { useTArray: true }));
  assert.deepEqual([top.width, top.height, bottom.width, bottom.height], [200, 220, 200, 220], "55% of the height each: 10% shared");
  assert.ok(top.data[0] < 80 && bottom.data[bottom.data.length - 4] > 170, "the top strip starts at the top, the bottom one ends at the bottom");
  assert.equal(pageStrips(page(200, 300), 3).length, 3);
});
test("no strips for what is not a JPEG page, or a count out of range", () => {
  assert.deepEqual(pageStrips(new Uint8Array([0x89, 0x50, 0x4e, 0x47]), 2), []);
  assert.deepEqual(pageStrips(new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3]), 2), [], "a broken JPEG");
  assert.deepEqual(pageStrips(page(50, 50), 1), []);
  assert.deepEqual(pageStrips(page(50, 50), 9), []);
});

test("strips are made where there is no Buffer global (a Worker), and none is left behind", () => {
  const saved = globalThis.Buffer, bytes = page(120, 160);
  delete globalThis.Buffer;
  try {
    const strips = pageStrips(bytes, 2);
    assert.equal(strips.length, 2); assert.ok(strips[0] instanceof Uint8Array); assert.equal(strips[0][0], 0xff);
    assert.equal(typeof globalThis.Buffer, "undefined");
  } finally { globalThis.Buffer = saved; }
});

test("a box of the page (0..1000, Gemini's box_2d) is cut out with its padding, clipped to the page", () => {
  const bytes = page(200, 400), cut = jpeg.decode(cropJpeg(bytes, [450, 100, 550, 300], 25, 50), { useTArray: true });
  assert.deepEqual([cut.width, cut.height], [60, 60], "rows 170-230 and columns 10-70");
  assert.ok(cut.data[0] < 80 && cut.data[cut.data.length - 4] > 170, "it straddles the dark top half and the light bottom half");
  const edge = jpeg.decode(cropJpeg(bytes, [0, 0, 100, 1000], 50, 50), { useTArray: true });
  assert.deepEqual([edge.width, edge.height], [200, 60]);
  assert.equal(cropJpeg(bytes, [500, 500, 501, 501], 0, 0), null, "too small to read");
  assert.equal(cropJpeg(bytes, [1, 2, 3]), null);
  assert.equal(cropJpeg(new Uint8Array([0x89, 0x50, 0x4e, 0x47]), [0, 0, 500, 500]), null);
});
