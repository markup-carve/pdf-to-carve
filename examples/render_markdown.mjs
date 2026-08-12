/** Generate comparison Markdown by dogfooding Carve's official JS renderer. */

import { readFileSync, writeFileSync } from 'node:fs'
import { carveToMarkdown } from '@markup-carve/carve'

const inputs = process.argv.slice(2)
if (inputs.length === 0) {
  throw new Error('usage: node render_markdown.mjs CASE/result.crv [...]')
}

for (const input of inputs) {
  if (!input.endsWith('/result.crv')) {
    throw new Error(`expected a result.crv path: ${input}`)
  }
  const output = input.slice(0, -'.crv'.length) + '.md'
  writeFileSync(output, carveToMarkdown(readFileSync(input, 'utf8')))
}
