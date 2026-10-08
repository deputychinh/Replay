// Turn every enum schema in openapi.json into an `as const` object + union type.
// The Python enums (backend/app/common/enums.py) stay the only source of truth.
import { readFileSync, writeFileSync } from 'node:fs';

const spec = JSON.parse(readFileSync(new URL('../openapi.json', import.meta.url), 'utf8'));
const key = (value) => value.toUpperCase().replace(/[^A-Z0-9]+/g, '_');

const blocks = Object.entries(spec.components.schemas)
  .filter(([, schema]) => Array.isArray(schema.enum))
  .sort(([a], [b]) => a.localeCompare(b))
  .map(([name, schema]) => {
    const entries = schema.enum.map((v) => `  ${key(v)}: ${JSON.stringify(v)},`).join('\n');
    return `export const ${name} = {\n${entries}\n} as const;\nexport type ${name} = (typeof ${name})[keyof typeof ${name}];`;
  });

writeFileSync(
  new URL('../src/enums.ts', import.meta.url),
  `// Generated from openapi.json by scripts/gen-enums.mjs — do not edit.\n\n${blocks.join('\n\n')}\n`,
);
console.log(`enums.ts: ${blocks.length} enums`);
