const IDENTIFIER = /^[A-Za-z_]\w*$/
const registeredMonaco = new WeakMap()

function cleanType(value) {
  return String(value || '').trim().replace(/\s+/g, ' ')
}

function inferExpressionType(expression, functions) {
  const value = String(expression || '').trim().replace(/\s+#.*$/, '')
  if (!value) return ''
  if (/^(?:True|False)$/.test(value)) return 'bool'
  if (value === 'None') return 'None'
  if (/^(?:f|r|u|b)?(['"]).*\1$/s.test(value)) return value.startsWith('b') ? 'bytes' : 'str'
  if (/^[+-]?\d+$/.test(value)) return 'int'
  if (/^[+-]?(?:\d+\.\d*|\d*\.\d+)(?:e[+-]?\d+)?$/i.test(value)) return 'float'
  if (/^\[\s*\]$/.test(value)) return 'list[Any]'
  if (/^\[/.test(value)) {
    const item = value.slice(1, -1).split(',').map(infer => inferExpressionType(infer, functions)).find(Boolean) || 'Any'
    return `list[${item}]`
  }
  if (/^\{\s*\}$/.test(value)) return 'dict[Any, Any]'
  if (/^\{/.test(value) && value.includes(':')) {
    const [key, item] = value.slice(1, -1).split(':', 2)
    return `dict[${inferExpressionType(key, functions) || 'Any'}, ${inferExpressionType(item, functions) || 'Any'}]`
  }
  if (/^\{/.test(value)) return 'set[Any]'
  if (/^\(/.test(value) && value.endsWith(')')) return 'tuple'
  const call = /^([A-Za-z_]\w*)\s*\(/.exec(value)
  if (call) {
    const name = call[1]
    if (functions.has(name)) return functions.get(name).returnType
    const builtins = { str: 'str', int: 'int', float: 'float', bool: 'bool', list: 'list', dict: 'dict', set: 'set', tuple: 'tuple', len: 'int', range: 'range', sum: 'int | float', enumerate: 'enumerate', zip: 'zip' }
    return builtins[name] || name
  }
  if (/^(?:await\s+)?[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$/.test(value)) return 'object'
  return ''
}

function parsePythonSymbols(source) {
  const functions = new Map()
  const variables = new Map()
  const lines = String(source || '').split('\n')
  const annotatedAssignments = /^\s*([A-Za-z_]\w*)\s*:\s*([^=]+?)(?:\s*=\s*(.*))?\s*(?:#.*)?$/
  const assignments = /^\s*([A-Za-z_]\w*)\s*(?::[^=]+)?=\s*(.*?)\s*(?:#.*)?$/
  const definitions = /^\s*def\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*(?:->\s*([^:]+))?\s*:/

  for (let index = 0; index < lines.length; index += 1) {
    const definition = definitions.exec(lines[index])
    if (definition) {
      let returnType = cleanType(definition[3])
      if (!returnType) {
        const baseIndent = lines[index].match(/^\s*/)[0].length
        const returns = []
        for (let row = index + 1; row < lines.length; row += 1) {
          const indent = lines[row].match(/^\s*/)[0].length
          if (lines[row].trim() && indent <= baseIndent) break
          const returned = /^\s*return\s+(.+?)\s*(?:#.*)?$/.exec(lines[row])
          if (returned) returns.push(inferExpressionType(returned[1], functions))
        }
        const types = [...new Set(returns.filter(Boolean))]
        returnType = types.length === 1 ? types[0] : types.length > 1 ? types.join(' | ') : 'None'
      }
      functions.set(definition[1], {
        returnType,
        signature: `(${definition[2].trim()}) -> ${returnType}`,
        line: index + 1,
      })
    }

    const annotated = annotatedAssignments.exec(lines[index])
    if (annotated) {
      const annotation = cleanType(annotated[2])
      const inferred = inferExpressionType(annotated[3], functions)
      variables.set(annotated[1], { type: annotation || inferred, inferredType: inferred, line: index + 1, declared: true })
      continue
    }
    const assignment = assignments.exec(lines[index])
    if (assignment && IDENTIFIER.test(assignment[1])) {
      const inferred = inferExpressionType(assignment[2], functions)
      if (inferred) variables.set(assignment[1], { type: inferred, line: index + 1, declared: false })
    }
  }
  return { functions, variables }
}

/** Add a small, dependency-free hover provider for learner Python code. */
export function registerPythonHoverProvider(monaco) {
  if (registeredMonaco.has(monaco)) return registeredMonaco.get(monaco)
  const provider = monaco.languages.registerHoverProvider('python', {
    provideHover(model, position) {
      const word = model.getWordAtPosition(position)
      if (!word) return null
      const { functions, variables } = parsePythonSymbols(model.getValue())
      const fn = functions.get(word.word)
      if (fn) {
        return {
          contents: [
            { value: `**function** \`${word.word}\`` },
            { value: `\`${fn.signature}\`` },
            { value: `Return type: \`${fn.returnType}\`` },
          ],
          range: new monaco.Range(position.lineNumber, word.startColumn, position.lineNumber, word.endColumn),
        }
      }
      const variable = variables.get(word.word)
      if (!variable?.type) return null
      const origin = variable.declared ? 'annotation' : 'inferred from assignment'
      const conflict = variable.inferredType && variable.inferredType !== variable.type
      return {
        contents: [
          { value: `**${word.word}**: \`${variable.type}\`` },
          ...(conflict ? [{ value: `Assigned value looks like \`${variable.inferredType}\`. Check that it matches the annotation.` }] : []),
          { value: `Python type ${origin} on line ${variable.line}.` },
        ],
        range: new monaco.Range(position.lineNumber, word.startColumn, position.lineNumber, word.endColumn),
      }
    },
  })
  registeredMonaco.set(monaco, provider)
  return provider
}
