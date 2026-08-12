#!/usr/bin/env node
import process from 'node:process';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createInterface } from 'node:readline/promises';
import fg from 'fast-glob';
import { Linter } from 'eslint';
import tseslint from 'typescript-eslint';

function isIdentifier(node) {
  return !!node && typeof node === "object" && node.type === "Identifier";
}
function isCallExpression(node) {
  return !!node && typeof node === "object" && node.type === "CallExpression";
}
function getRequiredRange(node) {
  if (!node.range) {
    throw new Error("Expected node to have a range.");
  }
  return node.range;
}
function isAstNode(node) {
  return !!node && typeof node === "object" && typeof node.type === "string";
}
function unwrapExpression(node) {
  let current = node;
  while (isAstNode(current)) {
    switch (current.type) {
      case "ParenthesizedExpression":
      case "TSAsExpression":
      case "TSSatisfiesExpression":
      case "TSNonNullExpression":
        current = current.expression;
        continue;
      default:
        return current;
    }
  }
  return current;
}
function getCallToLocalNames(node, localNames) {
  const unwrappedNode = unwrapExpression(node);
  return isCallExpression(unwrappedNode) && isIdentifier(unwrappedNode.callee) && localNames.has(unwrappedNode.callee.name) ? unwrappedNode : void 0;
}
function visitAst(node, visitor, parent = null) {
  if (!isAstNode(node)) {
    return;
  }
  visitor(node, parent);
  for (const [key, value] of Object.entries(node)) {
    if (key === "parent" || key === "range" || key === "loc") {
      continue;
    }
    if (Array.isArray(value)) {
      for (const item of value) {
        visitAst(item, visitor, node);
      }
      continue;
    }
    visitAst(value, visitor, node);
  }
}
function getNodeText(sourceCode, node) {
  return sourceCode.getText(node);
}
function getStatementRemovalRange(sourceCode, statement) {
  const text = sourceCode.getText();
  const range = getRequiredRange(statement);
  let start = range[0];
  while (start > 0 && text[start - 1] !== "\n") {
    start--;
  }
  let end = range[1];
  while (end < text.length && text[end] !== "\n") {
    end++;
  }
  if (text[end] === "\n") {
    end++;
  }
  let nextLineEnd = end;
  while (nextLineEnd < text.length && text[nextLineEnd] !== "\n") {
    nextLineEnd++;
  }
  if (text.slice(end, nextLineEnd).trim() === "") {
    end = nextLineEnd;
    if (text[end] === "\n") {
      end++;
    }
  }
  return [start, end];
}

const MIGRATION_PLUGIN_NAME = "vue-ts-migrate";
const MIGRATION_RULE_NAME = "to-with-vue-ts";
const MIGRATION_RULE_ID = `${MIGRATION_PLUGIN_NAME}/${MIGRATION_RULE_NAME}`;
const PACKAGE_NAME = "@vue/eslint-config-typescript";
const LEGACY_HELPER_IMPORTS = /* @__PURE__ */ new Set(["defineConfigWithVueTs", "defineConfig"]);
const PROJECT_OPTIONS_KEYS = /* @__PURE__ */ new Set([
  "tsSyntaxInTemplates",
  "scriptLangs",
  "allowComponentTypeUnsafety",
  "includeDotFolders",
  "rootDir"
]);
function isTsConfigFile(filename) {
  return [".ts", ".mts"].includes(path.extname(filename));
}
function getLintFilename(filename) {
  return path.basename(filename);
}
function getBaseConfig(filename) {
  return [
    {
      files: [
        "**/*.js",
        "**/*.mjs",
        "**/*.ts",
        "**/*.mts",
        "eslint.config.js",
        "eslint.config.mjs",
        "eslint.config.ts",
        "eslint.config.mts",
        "**/eslint.config.js",
        "**/eslint.config.mjs",
        "**/eslint.config.ts",
        "**/eslint.config.mts"
      ],
      languageOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ...isTsConfigFile(filename) ? { parser: tseslint.parser } : {}
      }
    }
  ];
}
function parseSourceCode(text, filename) {
  const lintFilename = getLintFilename(filename);
  const linter = new Linter({ configType: "flat" });
  const messages = linter.verify(text, getBaseConfig(lintFilename), {
    filename: lintFilename
  });
  const sourceCode = linter.getSourceCode();
  if (!sourceCode) {
    return {
      error: messages.find((message) => message.fatal)?.message ?? messages[0]?.message
    };
  }
  return {
    sourceCode
  };
}
function getImportSpecifierImportedName(specifier) {
  if (specifier.type !== "ImportSpecifier") {
    return;
  }
  if (typeof specifier.imported === "string") {
    return specifier.imported;
  }
  const imported = specifier.imported;
  return imported.name ?? imported.value;
}
function collectVueImports(sourceCode) {
  const declarations = [];
  const legacyHelperLocalNames = /* @__PURE__ */ new Set();
  const configureVueProjectLocalNames = /* @__PURE__ */ new Set();
  let withVueTsLocalName;
  const unsupportedReasons = [];
  for (const statement of sourceCode.ast.body) {
    if (statement.type !== "ImportDeclaration") {
      continue;
    }
    if (statement.source.value !== PACKAGE_NAME) {
      continue;
    }
    declarations.push(statement);
    for (const specifier of statement.specifiers) {
      if (specifier.type === "ImportDefaultSpecifier") {
        unsupportedReasons.push(
          "Default `createConfig()` imports are not supported by this migration yet."
        );
        continue;
      }
      if (specifier.type === "ImportNamespaceSpecifier") {
        unsupportedReasons.push(
          "Namespace imports from `@vue/eslint-config-typescript` are not supported by this migration yet."
        );
        continue;
      }
      const importedName = getImportSpecifierImportedName(specifier);
      if (!importedName) {
        continue;
      }
      if (LEGACY_HELPER_IMPORTS.has(importedName)) {
        legacyHelperLocalNames.add(specifier.local.name);
      }
      if (importedName === "configureVueProject") {
        configureVueProjectLocalNames.add(specifier.local.name);
      }
      if (importedName === "withVueTs") {
        withVueTsLocalName = specifier.local.name;
      }
      if (importedName === "createConfig") {
        unsupportedReasons.push(
          "`createConfig()` uses the older array-spread API and is not supported by this migration yet."
        );
      }
    }
  }
  return {
    declarations,
    legacyHelperLocalNames,
    configureVueProjectLocalNames,
    withVueTsLocalName,
    unsupportedReasons
  };
}
function findConfigureVueProjectStatements(sourceCode, localNames) {
  if (localNames.size === 0) {
    return [];
  }
  return sourceCode.ast.body.flatMap((statement) => {
    if (statement.type !== "ExpressionStatement") {
      return [];
    }
    const call = getCallToLocalNames(statement.expression, localNames);
    return call ? [{ statement, call }] : [];
  });
}
function findLocalNameUsages(sourceCode, localNames) {
  const usages = [];
  visitAst(sourceCode.ast, (node, parent) => {
    if (node.type !== "Identifier" || !localNames.has(node.name)) {
      return;
    }
    usages.push({
      identifier: node,
      parent
    });
  });
  return usages;
}
function isIgnoredConfigureUsage(usage, supportedCalls) {
  const { identifier, parent } = usage;
  if (!parent) {
    return false;
  }
  if ((parent.type === "ImportSpecifier" || parent.type === "ImportDefaultSpecifier" || parent.type === "ImportNamespaceSpecifier") && (parent.local === identifier || parent.imported === identifier)) {
    return true;
  }
  if ((parent.type === "Property" || parent.type === "PropertyDefinition" || parent.type === "MethodDefinition") && parent.key === identifier && !parent.computed) {
    return true;
  }
  if (parent.type === "MemberExpression" && parent.property === identifier && !parent.computed) {
    return true;
  }
  if (parent.type === "CallExpression" && parent.callee === identifier && supportedCalls.has(parent)) {
    return true;
  }
  return false;
}
function findLegacyTarget(sourceCode, localNames) {
  if (localNames.size === 0) {
    return;
  }
  const topLevelVariables = /* @__PURE__ */ new Map();
  for (const statement of sourceCode.ast.body) {
    if (statement.type !== "VariableDeclaration") {
      continue;
    }
    if (statement.kind !== "const" && statement.kind !== "let" && statement.kind !== "var") {
      continue;
    }
    for (const declaration of statement.declarations) {
      if (!isIdentifier(declaration.id)) {
        continue;
      }
      const call = getCallToLocalNames(declaration.init, localNames);
      if (!call) {
        continue;
      }
      topLevelVariables.set(declaration.id.name, { call, kind: statement.kind });
    }
  }
  const exportDefault = sourceCode.ast.body.find(
    (statement) => statement.type === "ExportDefaultDeclaration"
  );
  if (!exportDefault) {
    return;
  }
  const directCall = getCallToLocalNames(exportDefault.declaration, localNames);
  if (directCall) {
    const callee = directCall.callee;
    return {
      call: directCall,
      helperLocalName: callee.name
    };
  }
  const unwrappedDeclaration = unwrapExpression(exportDefault.declaration);
  if (!isIdentifier(unwrappedDeclaration)) {
    return;
  }
  const target = topLevelVariables.get(unwrappedDeclaration.name);
  if (!target || target.kind !== "const" || !isIdentifier(target.call.callee)) {
    return;
  }
  return {
    call: target.call,
    helperLocalName: target.call.callee.name
  };
}
function formatMultilineCall(calleeText, argsText) {
  if (argsText.length === 0) {
    return `${calleeText}()`;
  }
  const formattedArgs = argsText.map(
    (arg) => arg.split("\n").map((line) => `  ${line}`).join("\n")
  ).join(",\n");
  return `${calleeText}(
${formattedArgs},
)`;
}
function buildImportEdits(sourceCode, imports, withVueTsLocalName) {
  const primaryImport = imports.find(
    (statement) => statement.specifiers.some(
      (specifier) => specifier.type === "ImportSpecifier" && getImportSpecifierImportedName(specifier) === "withVueTs"
    )
  ) ?? imports[0];
  return imports.map((statement) => {
    const keptNamedSpecifiers = statement.specifiers.filter(
      (specifier) => specifier.type === "ImportSpecifier" && !LEGACY_HELPER_IMPORTS.has(
        getImportSpecifierImportedName(specifier) ?? ""
      ) && getImportSpecifierImportedName(specifier) !== "configureVueProject"
    ).map((specifier) => sourceCode.getText(specifier));
    const hasWithVueTsSpecifier = statement.specifiers.some(
      (specifier) => specifier.type === "ImportSpecifier" && getImportSpecifierImportedName(specifier) === "withVueTs"
    );
    if (statement === primaryImport && !hasWithVueTsSpecifier) {
      keptNamedSpecifiers.unshift(
        withVueTsLocalName === "withVueTs" ? "withVueTs" : `withVueTs as ${withVueTsLocalName}`
      );
    }
    if (keptNamedSpecifiers.length === 0) {
      return {
        range: getStatementRemovalRange(sourceCode, statement),
        text: ""
      };
    }
    const statementText = sourceCode.getText(statement);
    const semicolon = statementText.trimEnd().endsWith(";") ? ";" : "";
    return {
      range: getRequiredRange(statement),
      text: `import { ${keptNamedSpecifiers.join(", ")} } from ${sourceCode.getText(statement.source)}${semicolon}`
    };
  }).filter((edit) => !!edit);
}
function classifyFirstArgument(call) {
  const firstArg = unwrapExpression(call.arguments[0]);
  if (!firstArg || typeof firstArg !== "object" || Array.isArray(firstArg) || firstArg.type !== "ObjectExpression") {
    return "config";
  }
  const properties = firstArg.properties;
  let sawProjectOptionKey = false;
  let sawNonProjectOptionKey = false;
  let sawAmbiguousProperty = false;
  for (const property of properties) {
    if (property.type === "SpreadElement") {
      sawAmbiguousProperty = true;
      continue;
    }
    if (property.type !== "Property" || property.computed) {
      sawAmbiguousProperty = true;
      continue;
    }
    let propertyName;
    if (property.key.type === "Identifier") {
      propertyName = property.key.name;
    } else if (property.key.type === "Literal" && typeof property.key.value === "string") {
      propertyName = property.key.value;
    }
    if (!propertyName) {
      sawAmbiguousProperty = true;
      continue;
    }
    if (PROJECT_OPTIONS_KEYS.has(propertyName)) {
      sawProjectOptionKey = true;
    } else {
      sawNonProjectOptionKey = true;
    }
  }
  if (sawProjectOptionKey && !sawNonProjectOptionKey && !sawAmbiguousProperty) {
    return "options";
  }
  if (sawProjectOptionKey || sawAmbiguousProperty) {
    return "ambiguous-options";
  }
  return "config";
}
function analyzeToWithVueTsMigrationText(text, filename) {
  const parsed = parseSourceCode(text, filename);
  if (!parsed.sourceCode) {
    return {
      status: "parse-error",
      reason: parsed.error ?? "Unknown parser error."
    };
  }
  return analyzeToWithVueTsMigrationSourceCode(parsed.sourceCode);
}
function analyzeToWithVueTsMigrationSourceCode(sourceCode) {
  const facts = collectMigrationFacts(sourceCode);
  if (facts.imports.declarations.length === 0) {
    return { status: "noop" };
  }
  const structuralUnsupportedReasons = getStructuralUnsupportedReasons(
    sourceCode,
    facts
  );
  if (structuralUnsupportedReasons.length > 0) {
    return {
      status: "unsupported",
      reasons: structuralUnsupportedReasons
    };
  }
  if (!facts.legacyTarget) {
    return { status: "noop" };
  }
  if (isAlreadyUsingWithVueTs(facts)) {
    return { status: "noop" };
  }
  const callUnsupportedReason = getLegacyCallUnsupportedReason(
    facts.legacyTarget.call
  );
  if (callUnsupportedReason) {
    return {
      status: "unsupported",
      reasons: [callUnsupportedReason]
    };
  }
  return buildFixableMigrationAnalysis(sourceCode, {
    ...facts,
    legacyTarget: facts.legacyTarget
  });
}
function collectMigrationFacts(sourceCode) {
  const imports = collectVueImports(sourceCode);
  return {
    imports,
    configureStatements: findConfigureVueProjectStatements(
      sourceCode,
      imports.configureVueProjectLocalNames
    ),
    legacyTarget: findLegacyTarget(sourceCode, imports.legacyHelperLocalNames)
  };
}
function getStructuralUnsupportedReasons(sourceCode, facts) {
  return [
    .../* @__PURE__ */ new Set([
      ...facts.imports.unsupportedReasons,
      ...getConfigureVueProjectUnsupportedReasons(sourceCode, facts),
      ...getLegacyTargetUnsupportedReasons(facts)
    ])
  ];
}
function getConfigureVueProjectUnsupportedReasons(sourceCode, facts) {
  const reasons = [];
  const configureUsages = findLocalNameUsages(
    sourceCode,
    facts.imports.configureVueProjectLocalNames
  );
  const supportedConfigureCalls = new Set(
    facts.configureStatements.map(
      (configureStatement) => configureStatement.call
    )
  );
  if (configureUsages.some(
    (usage) => !isIgnoredConfigureUsage(usage, supportedConfigureCalls)
  )) {
    reasons.push(
      "Only top-level `configureVueProject(...)` calls are supported by this migration."
    );
  }
  if (facts.configureStatements.length > 1) {
    reasons.push(
      "Multiple `configureVueProject()` calls are not supported by this migration."
    );
  }
  return reasons;
}
function getLegacyTargetUnsupportedReasons(facts) {
  const reasons = [];
  if (facts.imports.legacyHelperLocalNames.size > 0 && !facts.legacyTarget) {
    reasons.push(
      "`defineConfigWithVueTs()` must be exported directly, or assigned to a top-level variable that is exported as default, for this migration to rewrite it safely."
    );
  }
  if (facts.configureStatements.length > 0 && !facts.legacyTarget) {
    reasons.push(
      "`configureVueProject()` was found, but this file does not export `defineConfigWithVueTs()`. Manual migration is required."
    );
  }
  return reasons;
}
function isAlreadyUsingWithVueTs(facts) {
  return !!facts.legacyTarget && !!facts.imports.withVueTsLocalName && facts.imports.withVueTsLocalName === facts.legacyTarget.helperLocalName;
}
function getLegacyCallUnsupportedReason(call) {
  const firstArgumentKind = classifyFirstArgument(call);
  if (firstArgumentKind === "options") {
    return "`defineConfigWithVueTs()` does not accept project options. This file appears to be partially migrated already.";
  }
  if (firstArgumentKind === "ambiguous-options") {
    return "The first argument to `defineConfigWithVueTs()` could be reinterpreted as `withVueTs()` project options. Please migrate this case manually.";
  }
}
function buildFixableMigrationAnalysis(sourceCode, facts) {
  const withVueTsLocalName = facts.imports.withVueTsLocalName ?? "withVueTs";
  const configureArgText = getConfigureVueProjectOptionsText(
    sourceCode,
    facts.configureStatements[0]
  );
  const replacementArgs = getWithVueTsReplacementArgs(
    sourceCode,
    facts.legacyTarget,
    configureArgText
  );
  const edits = buildMigrationEdits(
    sourceCode,
    facts,
    withVueTsLocalName,
    replacementArgs
  );
  const changes = getMigrationChanges(
    facts.legacyTarget.helperLocalName,
    withVueTsLocalName,
    configureArgText
  );
  return {
    status: "fixable",
    changes,
    edits
  };
}
function getConfigureVueProjectOptionsText(sourceCode, configureStatement) {
  const firstArg = configureStatement?.call.arguments[0];
  return firstArg === void 0 ? void 0 : getNodeText(sourceCode, firstArg);
}
function getWithVueTsReplacementArgs(sourceCode, legacyTarget, configureArgText) {
  return [
    ...configureArgText ? [configureArgText] : [],
    ...legacyTarget.call.arguments.map(
      (argument) => getNodeText(sourceCode, argument)
    )
  ];
}
function buildMigrationEdits(sourceCode, facts, withVueTsLocalName, replacementArgs) {
  const edits = [
    {
      range: getRequiredRange(facts.legacyTarget.call),
      text: formatMultilineCall(withVueTsLocalName, replacementArgs)
    },
    ...buildImportEdits(
      sourceCode,
      facts.imports.declarations,
      withVueTsLocalName
    )
  ];
  if (facts.configureStatements[0]) {
    edits.push({
      range: getStatementRemovalRange(
        sourceCode,
        facts.configureStatements[0].statement
      ),
      text: ""
    });
  }
  return edits.sort((a, b) => a.range[0] - b.range[0]);
}
function getMigrationChanges(legacyHelperLocalName, withVueTsLocalName, configureArgText) {
  return [
    `replace \`${legacyHelperLocalName}(...)\` with \`${withVueTsLocalName}(...)\``,
    "rewrite imports from `@vue/eslint-config-typescript`",
    ...configureArgText ? ["inline `configureVueProject(...)` options into `withVueTs(...)`"] : []
  ];
}
const migrateToWithVueTsRule = {
  meta: {
    type: "suggestion",
    fixable: "code",
    docs: {
      description: "migrate legacy @vue/eslint-config-typescript helper usage to withVueTs"
    },
    schema: [],
    messages: {
      migrate: "Legacy @vue/eslint-config-typescript helper usage can be migrated to `withVueTs(...)`."
    }
  },
  create(context) {
    return {
      Program(node) {
        const analysis = analyzeToWithVueTsMigrationSourceCode(
          context.sourceCode
        );
        if (analysis.status !== "fixable") {
          return;
        }
        context.report({
          node,
          messageId: "migrate",
          fix(fixer) {
            return analysis.edits.map(
              (edit) => fixer.replaceTextRange(edit.range, edit.text)
            );
          }
        });
      }
    };
  }
};
function getFixConfig(filename) {
  return [
    {
      ...getBaseConfig(filename)[0],
      plugins: {
        [MIGRATION_PLUGIN_NAME]: {
          rules: {
            [MIGRATION_RULE_NAME]: migrateToWithVueTsRule
          }
        }
      },
      rules: {
        [MIGRATION_RULE_ID]: "error"
      }
    }
  ];
}
function applyToWithVueTsMigrationText(text, filename) {
  const analysis = analyzeToWithVueTsMigrationText(text, filename);
  if (analysis.status !== "fixable") {
    return {
      analysis,
      changed: false,
      output: text
    };
  }
  const linter = new Linter({ configType: "flat" });
  const lintFilename = getLintFilename(filename);
  const report = linter.verifyAndFix(text, getFixConfig(lintFilename), {
    filename: lintFilename
  });
  return {
    analysis,
    changed: report.fixed,
    output: report.output ?? text
  };
}

const DEFAULT_PATTERNS = ["**/eslint.config.{js,mjs,ts,mts}"];
const DEFAULT_IGNORE = ["**/node_modules/**", "**/.git/**", "**/dist/**"];
function isFixableCandidate(candidate) {
  return candidate.analysis.status === "fixable";
}
function isUnsupportedCandidate(candidate) {
  return candidate.analysis.status === "unsupported" || candidate.analysis.status === "parse-error";
}
function parseArgs(argv) {
  return {
    yes: argv.includes("--yes") || argv.includes("-y"),
    help: argv.includes("--help") || argv.includes("-h"),
    patterns: argv.filter(
      (arg) => !["--yes", "-y", "--help", "-h"].includes(arg)
    )
  };
}
function printHelp$1() {
  console.log(`Usage:
  vue-eslint-config-typescript migrate-to-with-vue-ts [paths...] [--yes]

Examples:
  npx @vue/eslint-config-typescript migrate-to-with-vue-ts
  npx @vue/eslint-config-typescript migrate-to-with-vue-ts eslint.config.ts
  npx @vue/eslint-config-typescript migrate-to-with-vue-ts "packages/*/eslint.config.ts" --yes
`);
}
async function resolveTargetFiles(patterns) {
  const targetPatterns = patterns.length > 0 ? patterns : DEFAULT_PATTERNS;
  const explicitFiles = [];
  const globPatterns = [];
  for (const pattern of targetPatterns) {
    const filename = path.resolve(pattern);
    const stat = await fs.stat(filename).catch(() => void 0);
    if (stat?.isFile()) {
      explicitFiles.push(filename);
      continue;
    }
    globPatterns.push(pattern);
  }
  const entries = await fg(globPatterns, {
    cwd: process.cwd(),
    absolute: true,
    onlyFiles: true,
    unique: true,
    ignore: DEFAULT_IGNORE
  });
  return [.../* @__PURE__ */ new Set([...explicitFiles, ...entries])].sort();
}
async function loadCandidates(filenames) {
  return Promise.all(
    filenames.map(async (filename) => {
      const text = await fs.readFile(filename, "utf8");
      return {
        filename,
        relativeFilename: path.relative(process.cwd(), filename) || path.basename(filename),
        analysis: analyzeToWithVueTsMigrationText(text, filename)
      };
    })
  );
}
function printSummary(candidates) {
  const fixable = candidates.filter(isFixableCandidate);
  const unsupported = candidates.filter(isUnsupportedCandidate);
  console.log(`Found ${candidates.length} ESLint config file(s).
`);
  if (fixable.length > 0) {
    console.log("Auto-migratable:");
    for (const candidate of fixable) {
      console.log(`- ${candidate.relativeFilename}`);
      for (const change of candidate.analysis.changes) {
        console.log(`  - ${change}`);
      }
    }
    console.log("");
  }
  if (unsupported.length > 0) {
    console.log("Needs manual review:");
    for (const candidate of unsupported) {
      console.log(`- ${candidate.relativeFilename}`);
      if (candidate.analysis.status === "parse-error") {
        console.log(`  - parser error: ${candidate.analysis.reason}`);
        continue;
      }
      for (const reason of candidate.analysis.reasons) {
        console.log(`  - ${reason}`);
      }
    }
    console.log("");
  }
  if (fixable.length === 0 && unsupported.length === 0) {
    console.log("No migration needed.\n");
  }
}
async function confirmApply() {
  const readline = createInterface({
    input: process.stdin,
    output: process.stdout
  });
  try {
    const answer = (await readline.question("Apply automatic changes? [Y/n] ")).trim().toLowerCase();
    return answer === "" || answer === "y" || answer === "yes";
  } finally {
    readline.close();
  }
}
async function applyFixes(candidates) {
  let updatedFiles = 0;
  for (const candidate of candidates) {
    if (candidate.analysis.status !== "fixable") {
      continue;
    }
    const input = await fs.readFile(candidate.filename, "utf8");
    const result = applyToWithVueTsMigrationText(input, candidate.filename);
    if (!result.changed) {
      continue;
    }
    await fs.writeFile(candidate.filename, result.output);
    updatedFiles += 1;
  }
  return updatedFiles;
}
async function runMigrateToWithVueTsCommand(argv) {
  const options = parseArgs(argv);
  if (options.help) {
    printHelp$1();
    return;
  }
  const filenames = await resolveTargetFiles(options.patterns);
  if (filenames.length === 0) {
    console.log("No matching ESLint config files found.");
    return;
  }
  const candidates = await loadCandidates(filenames);
  printSummary(candidates);
  const fixableCount = candidates.filter(isFixableCandidate).length;
  if (fixableCount === 0) {
    return;
  }
  if (!options.yes && !process.stdin.isTTY) {
    console.log(
      "Cannot prompt in a non-interactive terminal. Re-run with `--yes` to apply the automatic changes."
    );
    return;
  }
  const shouldApply = options.yes ? true : await confirmApply();
  if (!shouldApply) {
    console.log("No files were changed.");
    return;
  }
  const updatedFiles = await applyFixes(candidates);
  console.log(`Updated ${updatedFiles} file(s).`);
}

const COMMANDS = {
  "migrate-to-with-vue-ts": runMigrateToWithVueTsCommand,
  "migrate-14.9": runMigrateToWithVueTsCommand
};
function printHelp() {
  console.log(`Usage:
  vue-eslint-config-typescript <command> [args]

Commands:
  migrate-to-with-vue-ts   Primary command. Migrate legacy helper-based configs to withVueTs(...)
  migrate-14.9             Versioned alias for migrate-to-with-vue-ts
`);
}
async function main() {
  const [command, ...args] = process.argv.slice(2);
  if (!command || command === "--help" || command === "-h") {
    printHelp();
    return;
  }
  const runCommand = COMMANDS[command];
  if (!runCommand) {
    console.error(`Unknown command: ${command}
`);
    printHelp();
    process.exitCode = 1;
    return;
  }
  await runCommand(args);
}
main().catch((error) => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  console.error(message);
  process.exitCode = 1;
});
