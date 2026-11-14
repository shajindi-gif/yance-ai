import { existsSync, cpSync, mkdirSync, rmSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root=resolve(dirname(fileURLToPath(import.meta.url)), '..');
const output=resolve(root,'.next/standalone');
if (!existsSync(resolve(output,'server.js'))) throw new Error('Standalone build is missing; run next build first.');
for (const [source,target] of [['public','public'],['.next/static','.next/static']]) {
  const input=resolve(root,source), destination=resolve(output,target);
  if (!existsSync(input)) throw new Error(`Build input is missing: ${source}`);
  // Only generated build directories are replaced; source assets are preserved.
  rmSync(destination,{recursive:true,force:true});
  mkdirSync(dirname(destination),{recursive:true});
  cpSync(input,destination,{recursive:true});
}
