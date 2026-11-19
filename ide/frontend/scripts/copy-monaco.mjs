// Copy Monaco's prebuilt AMD distribution into public/monaco so the editor
// loads offline from the same origin, with every language and worker, without
// Rollup having to bundle Monaco (which needed more RAM than small machines have).
import { cpSync, existsSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const projectDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const source = path.join(projectDir, 'node_modules', 'monaco-editor', 'min')
const target = path.join(projectDir, 'public', 'monaco')
const marker = path.join(target, '.version')
const version = JSON.parse(readFileSync(path.join(projectDir, 'node_modules', 'monaco-editor', 'package.json'), 'utf8')).version

if (existsSync(marker) && readFileSync(marker, 'utf8') === version) process.exit(0)
rmSync(target, { recursive: true, force: true })
cpSync(source, target, { recursive: true, dereference: true })
writeFileSync(marker, version)
console.log(`monaco-editor ${version} copied to public/monaco`)
