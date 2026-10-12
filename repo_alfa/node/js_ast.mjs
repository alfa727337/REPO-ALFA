#!/usr/bin/env node
import fs from 'node:fs';
import process from 'node:process';
import { parse } from '@babel/parser';
import traverseModule from '@babel/traverse';

const traverse = traverseModule.default || traverseModule;
const file = process.argv[2];
if (!file) {
  console.error('usage: node js_ast.mjs <file>');
  process.exit(2);
}

const source = fs.readFileSync(file, 'utf8');
const result = {
  file,
  parsed: false,
  imports: [],
  exports: [],
  dynamicImports: [],
  requires: [],
  fetchCalls: [],
  axiosCalls: [],
  websocketConstructors: [],
  functions: [],
  classes: [],
  stringUrls: [],
  nodeCounts: {},
  error: null
};

const urlLike = /^(?:https?:\/\/|wss?:\/\/|\/api\/|\/graphql|\/_next\/|\/_nuxt\/|\/_app\/)/;
const add = (array, value) => {
  if (typeof value === 'string' && value && !array.includes(value)) array.push(value);
};
const literalValue = node => {
  if (!node) return null;
  if (node.type === 'StringLiteral') return node.value;
  if (node.type === 'TemplateLiteral' && node.expressions.length === 0) {
    return node.quasis.map(q => q.value.cooked ?? q.value.raw).join('');
  }
  return null;
};

try {
  const ast = parse(source, {
    sourceType: 'unambiguous',
    errorRecovery: true,
    allowAwaitOutsideFunction: true,
    allowReturnOutsideFunction: true,
    plugins: [
      'jsx',
      'typescript',
      'dynamicImport',
      'importMeta',
      'topLevelAwait',
      'optionalChaining',
      'classProperties',
      'classPrivateProperties',
      'classPrivateMethods',
      'decorators-legacy'
    ]
  });
  result.parsed = true;

  traverse(ast, {
    enter(path) {
      const type = path.node.type;
      result.nodeCounts[type] = (result.nodeCounts[type] || 0) + 1;
    },
    ImportDeclaration(path) {
      add(result.imports, path.node.source?.value);
    },
    ExportNamedDeclaration(path) {
      if (path.node.source?.value) add(result.exports, path.node.source.value);
    },
    ExportAllDeclaration(path) {
      add(result.exports, path.node.source?.value);
    },
    Import(path) {
      const parent = path.parentPath?.node;
      if (parent?.type === 'CallExpression') {
        add(result.dynamicImports, literalValue(parent.arguments?.[0]));
      }
    },
    CallExpression(path) {
      const node = path.node;
      if (node.callee?.type === 'Identifier' && node.callee.name === 'require') {
        add(result.requires, literalValue(node.arguments?.[0]));
      }
      if (node.callee?.type === 'Identifier' && node.callee.name === 'fetch') {
        add(result.fetchCalls, literalValue(node.arguments?.[0]));
      }
      if (node.callee?.type === 'MemberExpression') {
        const objectName = node.callee.object?.name;
        const propertyName = node.callee.property?.name || node.callee.property?.value;
        if (objectName === 'axios' && propertyName) {
          const target = literalValue(node.arguments?.[0]);
          add(result.axiosCalls, `${propertyName}:${target ?? '<dynamic>'}`);
        }
      }
    },
    NewExpression(path) {
      const node = path.node;
      if (node.callee?.type === 'Identifier' && node.callee.name === 'WebSocket') {
        add(result.websocketConstructors, literalValue(node.arguments?.[0]) ?? '<dynamic>');
      }
    },
    FunctionDeclaration(path) {
      add(result.functions, path.node.id?.name || '<anonymous>');
    },
    ClassDeclaration(path) {
      add(result.classes, path.node.id?.name || '<anonymous>');
    },
    StringLiteral(path) {
      if (urlLike.test(path.node.value)) add(result.stringUrls, path.node.value);
    },
    TemplateElement(path) {
      const value = path.node.value?.cooked ?? path.node.value?.raw;
      if (urlLike.test(value || '')) add(result.stringUrls, value);
    }
  });
} catch (error) {
  result.error = String(error?.stack || error);
}

for (const key of [
  'imports','exports','dynamicImports','requires','fetchCalls','axiosCalls',
  'websocketConstructors','functions','classes','stringUrls'
]) {
  result[key].sort();
}
result.nodeCounts = Object.fromEntries(
  Object.entries(result.nodeCounts).sort((a, b) => b[1] - a[1])
);
process.stdout.write(JSON.stringify(result));
