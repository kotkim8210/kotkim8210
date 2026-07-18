// Packs the CrazyGames build (dist-portal/) into blocknova-portal.zip and
// reports bundle sizes (target: ≤ 2MB, CLAUDE.md Phase 4).
import AdmZip from 'adm-zip';
import { readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const DIST = 'dist-portal';
const OUT = 'blocknova-portal.zip';

function walk(dir) {
  let total = 0;
  const rows = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) {
      const sub = walk(p);
      total += sub.total;
      rows.push(...sub.rows);
    } else {
      total += st.size;
      rows.push([p, st.size]);
    }
  }
  return { total, rows };
}

const zip = new AdmZip();
zip.addLocalFolder(DIST);
zip.writeZip(OUT);

const { total, rows } = walk(DIST);
const kb = (n) => `${(n / 1024).toFixed(1)} KB`;
console.log(`\n${OUT} written (${kb(statSync(OUT).size)})`);
console.log(`uncompressed bundle: ${kb(total)} — target ≤ 2 MB: ${total <= 2 * 1024 * 1024 ? 'OK' : 'OVER'}`);
for (const [p, size] of rows) console.log(`  ${kb(size).padStart(10)}  ${p}`);
