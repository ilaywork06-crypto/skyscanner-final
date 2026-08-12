import process$1 from 'node:process';
import tseslint from 'typescript-eslint';
import pluginVue from 'eslint-plugin-vue';
import fs from 'node:fs';
import fg from 'fast-glob';
import path from 'node:path';
import { debuglog } from 'node:util';
import vueParser from 'vue-eslint-parser';

const CONFIG_NAMES = [
  "all",
  "base",
  "disableTypeChecked",
  "eslintRecommended",
  "recommended",
  "recommendedTypeChecked",
  "recommendedTypeCheckedOnly",
  "strict",
  "strictTypeChecked",
  "strictTypeCheckedOnly",
  "stylistic",
  "stylisticTypeChecked",
  "stylisticTypeCheckedOnly"
];
function toArray(value) {
  return Array.isArray(value) ? value : [value];
}
const VUE_TS_CONFIG = Symbol("@vue/eslint-config-typescript/vue-ts-config");
const TS_FILES_GLOB = "**/*.ts";
const VUE_FILES_GLOB = "**/*.vue";
function needsTypeChecking(configName) {
  if (configName === "disableTypeChecked") {
    return false;
  }
  if (configName === "all") {
    return true;
  }
  return configName.includes("TypeChecked");
}
function markVueTsConfig(config, meta) {
  return {
    ...config,
    [VUE_TS_CONFIG]: meta
  };
}
function createVueTsConfig(configName) {
  const meta = {
    configName,
    needsTypeChecking: needsTypeChecking(configName)
  };
  return toArray(tseslint.configs[configName]).flat().map((config) => markVueTsConfig(config, meta));
}
function hasTsMatcher(files) {
  return files.some(
    (fileMatcher) => Array.isArray(fileMatcher) ? fileMatcher.includes(TS_FILES_GLOB) : fileMatcher === TS_FILES_GLOB
  );
}
function addVueMatcher(files) {
  const vueMatchers = files.reduce(
    (result, fileMatcher) => {
      if (Array.isArray(fileMatcher)) {
        if (fileMatcher.includes(TS_FILES_GLOB)) {
          result.push(
            fileMatcher.map(
              (matcher) => matcher === TS_FILES_GLOB ? VUE_FILES_GLOB : matcher
            )
          );
        }
        return result;
      }
      if (fileMatcher === TS_FILES_GLOB) {
        result.push(VUE_FILES_GLOB);
      }
      return result;
    },
    []
  );
  return vueMatchers.length > 0 ? [...files, ...vueMatchers] : files;
}
function isVueTsConfig(config) {
  return VUE_TS_CONFIG in config;
}
function extendVueTsConfig(config, restOfConfig) {
  const name = [restOfConfig.name, config.name].filter(Boolean).join("__");
  return {
    ...config,
    ...restOfConfig.files && { files: restOfConfig.files },
    ...restOfConfig.ignores && { ignores: restOfConfig.ignores },
    ...name && { name }
  };
}
function vueTsConfigNeedsTypeChecking(config) {
  return config[VUE_TS_CONFIG].needsTypeChecking;
}
function resolveVueTsConfig(config) {
  const { [VUE_TS_CONFIG]: _meta, ...resolvedConfig } = config;
  return {
    ...resolvedConfig,
    ...resolvedConfig.files && hasTsMatcher(resolvedConfig.files) ? { files: addVueMatcher(resolvedConfig.files) } : {}
  };
}
const vueTsConfigs = Object.fromEntries(
  CONFIG_NAMES.map((name) => [name, createVueTsConfig(name)])
);

const debug = debuglog("@vue/eslint-config-typescript:groupVueFiles");
function groupVueFiles(rootDir, globalIgnores, includeDotFolders) {
  debug(`Grouping .vue files in ${rootDir}`);
  const ignore = [
    "**/node_modules/**",
    "**/.git/**",
    // Global ignore patterns from ESLint config are relative to the ESLint base path,
    // which is usually the cwd, but could be different if `--config` is provided via CLI.
    // This is way too complicated, so we only use process.cwd() as a best-effort guess here.
    // Could be improved in the future if needed.
    ...globalIgnores.map(
      (pattern) => fg.convertPathToPattern(path.resolve(process.cwd(), pattern))
    )
  ];
  debug(`Ignoring patterns: ${ignore.join(", ")}`);
  const { vueFilesWithScriptTs, otherVueFiles } = fg.sync(["**/*.vue"], {
    cwd: rootDir,
    ignore,
    dot: includeDotFolders
  }).reduce(
    (acc, file) => {
      const absolutePath = path.resolve(rootDir, file);
      const contents = fs.readFileSync(absolutePath, "utf8");
      if (/<script[^>]*\blang\s*=\s*"ts"[^>]*>/i.test(contents)) {
        acc.vueFilesWithScriptTs.push(file);
      } else {
        acc.otherVueFiles.push(file);
      }
      return acc;
    },
    { vueFilesWithScriptTs: [], otherVueFiles: [] }
  );
  return {
    // Only `.vue` files with `<script lang="ts">` or `<script setup lang="ts">` can be type-checked.
    typeCheckable: vueFilesWithScriptTs,
    nonTypeCheckable: otherVueFiles
  };
}

const extraFileExtensions = [".vue"];
function escapePathForGlob(path) {
  return path.replace(/([*?{}[\]()])/g, "[$1]");
}
const additionalRulesRequiringParserServices = [
  "@typescript-eslint/consistent-type-imports",
  "@typescript-eslint/prefer-optional-chain"
];
function createBasicSetupConfigs(tsSyntaxInTemplates, scriptLangs) {
  const mayHaveJsxInSfc = scriptLangs.includes("jsx") || scriptLangs.includes("tsx");
  const parser = {
    // Fallback to espree for js/jsx scripts, as well as SFCs without scripts
    // for better performance.
    js: "espree",
    jsx: "espree",
    ts: tseslint.parser,
    tsx: tseslint.parser
    // Leave the template parser unspecified,
    // so that it could be determined by `<script lang="...">`
  };
  if (!tsSyntaxInTemplates) {
    parser["<template>"] = "espree";
  }
  return [
    // Must set eslint-plugin-vue's base config again no matter whether the user
    // has set it before. Otherwise it would be overridden by the tseslint's config.
    ...pluginVue.configs["flat/base"],
    {
      name: "@vue/typescript/setup",
      files: ["*.vue", "**/*.vue"],
      languageOptions: {
        parser: vueParser,
        parserOptions: {
          parser,
          // The internal espree version used by vue-eslint-parser is 9.x, which supports ES2024 at most.
          // While the parser may try to load the latest version of espree, it's not guaranteed to work.
          // For example, if npm accidentally hoists the older version to the top of the node_modules,
          // or if the user installs the older version of espree at the project root,
          // the older versions would be used.
          // But ESLint 9 allows setting the ecmaVersion to 2025, which may cause a crash.
          // So we set the ecmaVersion to 2024 here to avoid the potential issue.
          ecmaVersion: 2024,
          ecmaFeatures: {
            jsx: mayHaveJsxInSfc
          },
          extraFileExtensions
        }
      },
      rules: {
        "vue/block-lang": [
          "error",
          {
            script: {
              lang: scriptLangs,
              allowNoLang: scriptLangs.includes("js")
            }
          }
        ]
      }
    }
  ];
}
function createSkipTypeCheckingConfigs(nonTypeCheckableVueFiles) {
  const configs = [
    {
      name: "@vue/typescript/skip-type-checking-for-js-files",
      files: ["**/*.js", "**/*.jsx", "**/*.cjs", "**/*.mjs"],
      ...tseslint.configs.disableTypeChecked
    }
  ];
  if (nonTypeCheckableVueFiles.length > 0) {
    configs.push({
      name: "@vue/typescript/skip-type-checking-for-vue-files-without-ts",
      files: nonTypeCheckableVueFiles.map(escapePathForGlob),
      ...tseslint.configs.disableTypeChecked,
      rules: {
        ...tseslint.configs.disableTypeChecked.rules,
        ...Object.fromEntries(
          additionalRulesRequiringParserServices.map((rule) => [rule, "off"])
        )
      }
    });
  }
  return configs;
}
function createTypeCheckingConfigs(typeCheckableVueFiles, allowComponentTypeUnsafety) {
  const configs = [
    {
      name: "@vue/typescript/default-project-service-for-ts-files",
      files: ["**/*.ts", "**/*.tsx", "**/*.mts"],
      languageOptions: {
        parser: tseslint.parser,
        parserOptions: {
          projectService: true,
          extraFileExtensions
        }
      }
    }
  ];
  if (allowComponentTypeUnsafety) {
    configs.push(
      // Due to limitations in the integration between Vue and TypeScript-ESLint,
      // TypeScript-ESLint cannot get the full type information for `.vue` files
      // and will use fallback types that contain some `any`s.
      // Therefore, we need to disable some `no-unsafe-*` rules that would error on idiomatic Vue code.
      {
        name: "@vue/typescript/type-aware-rules-in-conflict-with-vue",
        files: ["**/*.ts", "**/*.tsx", "**/*.mts", "**/*.vue"],
        rules: {
          // Would error on `createApp(App)`
          "@typescript-eslint/no-unsafe-argument": "off",
          // Would error on route component configuration
          "@typescript-eslint/no-unsafe-assignment": "off",
          // Would error on async components
          "@typescript-eslint/no-unsafe-return": "off",
          // Might error on `defineExpose` + `useTemplateRef` usages
          "@typescript-eslint/no-unsafe-call": "off",
          "@typescript-eslint/no-unsafe-member-access": "off"
        }
      }
    );
  }
  if (typeCheckableVueFiles.length > 0) {
    configs.push({
      name: "@vue/typescript/default-project-service-for-vue-files",
      files: typeCheckableVueFiles.map(escapePathForGlob),
      languageOptions: {
        parser: vueParser,
        parserOptions: {
          projectService: true,
          parser: tseslint.parser,
          extraFileExtensions
        }
      }
    });
  }
  return configs;
}

function omit(obj, keys) {
  return Object.fromEntries(
    Object.entries(obj).filter(([key]) => !keys.includes(key))
  );
}
const pipe = (value, ...fns) => {
  return fns.reduce((acc, fn) => fn(acc), value);
};
function partition(array, predicate) {
  const truthy = [];
  const falsy = [];
  for (const element of array) {
    if (predicate(element)) {
      truthy.push(element);
    } else {
      falsy.push(element);
    }
  }
  return [truthy, falsy];
}

const PROJECT_OPTION_KEYS = /* @__PURE__ */ new Set([
  "tsSyntaxInTemplates",
  "scriptLangs",
  "allowComponentTypeUnsafety",
  "includeDotFolders",
  "rootDir"
]);
const DEFAULT_PROJECT_OPTIONS = {
  tsSyntaxInTemplates: true,
  scriptLangs: ["ts"],
  allowComponentTypeUnsafety: true,
  includeDotFolders: false,
  rootDir: process$1.cwd()
};
let projectOptions = { ...DEFAULT_PROJECT_OPTIONS };
function resolveProjectOptions(userOptions = {}) {
  return {
    tsSyntaxInTemplates: userOptions.tsSyntaxInTemplates ?? projectOptions.tsSyntaxInTemplates,
    scriptLangs: userOptions.scriptLangs ?? projectOptions.scriptLangs,
    allowComponentTypeUnsafety: userOptions.allowComponentTypeUnsafety ?? projectOptions.allowComponentTypeUnsafety,
    includeDotFolders: userOptions.includeDotFolders ?? projectOptions.includeDotFolders,
    rootDir: userOptions.rootDir ?? projectOptions.rootDir
  };
}
function createTransformState() {
  return {
    globalIgnores: [],
    userTypeAwareConfigs: []
  };
}
function normalizeConfigInput(config) {
  return Array.isArray(config) ? config : [config];
}
function isPlainObject(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}
function classifyFirstArg(value) {
  if (!isPlainObject(value)) {
    return "config";
  }
  const keys = Object.keys(value);
  if (keys.length === 0) {
    return "config";
  }
  const optionKeyCount = keys.filter((key) => PROJECT_OPTION_KEYS.has(key)).length;
  if (optionKeyCount === 0) {
    return "config";
  }
  if (optionKeyCount === keys.length) {
    return "options";
  }
  return "mixed-options-and-config";
}
function splitOptionsAndConfigInputs(args) {
  if (args.length === 0) {
    return {
      configInputs: [],
      userOptions: {}
    };
  }
  const firstArg = args[0];
  const firstArgKind = classifyFirstArg(firstArg);
  if (firstArgKind === "mixed-options-and-config") {
    throw new TypeError(
      "The first argument to `withVueTs(...)` cannot mix Vue project options with ESLint config keys. Pass project options as the first argument and move ESLint config fields into a separate config object."
    );
  }
  if (firstArgKind !== "options") {
    return {
      configInputs: args,
      userOptions: {}
    };
  }
  return {
    configInputs: args.slice(1),
    userOptions: firstArg
  };
}
function applyVueTsTransform(configs, options) {
  const state = createTransformState();
  return pipe(
    configs,
    flattenConfigs,
    (rawConfigs) => collectGlobalIgnores(rawConfigs, state),
    deduplicateVuePlugin,
    (rawConfigs) => insertAndReorderConfigs(rawConfigs, options, state),
    resolveVueTsConfigs,
    tseslint.config
    // this might not be necessary, but it doesn't hurt to keep it
  );
}
function configureVueProject(userOptions) {
  if (userOptions.tsSyntaxInTemplates !== void 0) {
    projectOptions.tsSyntaxInTemplates = userOptions.tsSyntaxInTemplates;
  }
  if (userOptions.allowComponentTypeUnsafety !== void 0) {
    projectOptions.allowComponentTypeUnsafety = userOptions.allowComponentTypeUnsafety;
  }
  if (userOptions.scriptLangs) {
    projectOptions.scriptLangs = userOptions.scriptLangs;
  }
  if (userOptions.rootDir) {
    projectOptions.rootDir = userOptions.rootDir;
  }
  if (userOptions.includeDotFolders !== void 0) {
    projectOptions.includeDotFolders = userOptions.includeDotFolders;
  }
}
function defineConfigWithVueTs(...configs) {
  return applyVueTsTransform(configs, resolveProjectOptions());
}
async function withVueTs(...args) {
  const { configInputs, userOptions } = splitOptionsAndConfigInputs(args);
  const resolvedConfigs = await Promise.all(configInputs);
  return applyVueTsTransform(
    resolvedConfigs.flatMap((config) => normalizeConfigInput(config)),
    resolveProjectOptions(userOptions)
  );
}
function flattenConfigs(configs) {
  const flattenedConfigs = configs.flat(
    Infinity
  );
  return flattenedConfigs.flatMap(
    (config) => {
      if (isVueTsConfig(config)) {
        return config;
      }
      const { extends: extendsArray, ...restOfConfig } = config;
      if (extendsArray == null || extendsArray.length === 0) {
        return restOfConfig;
      }
      const flattenedExtends = extendsArray.flatMap(
        (configToExtend) => Array.isArray(configToExtend) ? flattenConfigs(configToExtend) : [configToExtend]
      );
      return [
        ...flattenedExtends.map((extension) => {
          if (isVueTsConfig(extension)) {
            return extendVueTsConfig(extension, restOfConfig);
          }
          const name = [restOfConfig.name, extension.name].filter(Boolean).join("__");
          return {
            ...extension,
            ...restOfConfig.files && { files: restOfConfig.files },
            ...restOfConfig.ignores && { ignores: restOfConfig.ignores },
            ...name && { name }
          };
        }),
        // If restOfConfig contains nothing but `ignores`/`name`, we shouldn't return it
        // Because that would make it a global `ignores` config, which is not what we want
        ...Object.keys(omit(restOfConfig, ["ignores", "name"])).length > 0 ? [restOfConfig] : []
      ];
    }
  );
}
const META_FIELDS = /* @__PURE__ */ new Set(["name", "basePath"]);
function collectGlobalIgnores(configs, state) {
  configs.forEach((config) => {
    if (isVueTsConfig(config) || !config.ignores) {
      return;
    }
    if (Object.keys(config).filter((key) => !META_FIELDS.has(key)).length !== 1)
      return;
    state.globalIgnores.push(...config.ignores);
  });
  return configs;
}
function resolveVueTsConfigs(configs) {
  return configs.map(
    (config) => isVueTsConfig(config) ? resolveVueTsConfig(config) : config
  );
}
function insertAndReorderConfigs(configs, options, state) {
  const lastExtendedConfigIndex = configs.findLastIndex(
    (config) => isVueTsConfig(config)
  );
  if (lastExtendedConfigIndex === -1) {
    return configs;
  }
  const vueFiles = groupVueFiles(
    options.rootDir,
    state.globalIgnores,
    options.includeDotFolders
  );
  const configsWithoutTypeAwareRules = configs.map(
    (config) => extractTypeAwareRules(config, state)
  );
  const hasTypeAwareConfigs = configs.some(
    (config) => isVueTsConfig(config) && vueTsConfigNeedsTypeChecking(config)
  );
  const needsTypeAwareLinting = hasTypeAwareConfigs || state.userTypeAwareConfigs.length > 0;
  return [
    ...configsWithoutTypeAwareRules.slice(0, lastExtendedConfigIndex + 1),
    ...createBasicSetupConfigs(
      options.tsSyntaxInTemplates,
      options.scriptLangs
    ),
    // user-turned-off type-aware rules must come after the last extended config
    // in case some rules re-enabled by the extended config
    // user-turned-on type-aware rules must come before skipping type-checking
    // in case some rules targets those can't be type-checked files
    // So we extract all type-aware rules by users and put them in the middle
    ...state.userTypeAwareConfigs,
    ...needsTypeAwareLinting ? [
      ...createSkipTypeCheckingConfigs(vueFiles.nonTypeCheckable),
      ...createTypeCheckingConfigs(
        vueFiles.typeCheckable,
        options.allowComponentTypeUnsafety
      )
    ] : [],
    ...configsWithoutTypeAwareRules.slice(lastExtendedConfigIndex + 1)
  ];
}
function extractTypeAwareRules(config, state) {
  if (isVueTsConfig(config) || !config.rules) {
    return config;
  }
  const [typeAwareRuleEntries, otherRuleEntries] = partition(
    Object.entries(config.rules),
    ([name]) => doesRuleRequireTypeInformation(name)
  );
  if (typeAwareRuleEntries.length > 0) {
    state.userTypeAwareConfigs.push({
      rules: Object.fromEntries(typeAwareRuleEntries),
      ...config.files && { files: config.files }
    });
  }
  return {
    ...config,
    rules: Object.fromEntries(otherRuleEntries)
  };
}
const rulesRequiringTypeInformation = new Set(
  Object.entries(tseslint.plugin.rules).filter(([_name, def]) => def?.meta?.docs?.requiresTypeChecking).map(([name, _def]) => `@typescript-eslint/${name}`).concat(additionalRulesRequiringParserServices)
);
function doesRuleRequireTypeInformation(ruleName) {
  return rulesRequiringTypeInformation.has(ruleName);
}
function deduplicateVuePlugin(configs) {
  return configs.map((config) => {
    if (isVueTsConfig(config) || !config.plugins?.vue) {
      return config;
    }
    const currentVuePlugin = config.plugins.vue;
    if (currentVuePlugin !== pluginVue) {
      const currentVersion = currentVuePlugin.meta?.version || "unknown";
      const expectedVersion = pluginVue.meta?.version || "unknown";
      const configName = config.name || "unknown config";
      console.warn(
        `Warning: Multiple instances of eslint-plugin-vue detected in ${configName}. Replacing version ${currentVersion} with version ${expectedVersion}.`
      );
      return {
        ...config,
        plugins: {
          ...config.plugins,
          vue: pluginVue
        }
      };
    }
    return config;
  });
}

function createConfig({
  extends: configNamesToExtend = ["recommended"],
  supportedScriptLangs = { ts: true, tsx: false, js: false, jsx: false },
  rootDir = process.cwd()
} = {}) {
  for (const name of configNamesToExtend) {
    if (!tseslint.configs[name]) {
      const nameInCamelCase = name.replace(
        /-([a-z])/g,
        (_, letter) => letter.toUpperCase()
      );
      if (tseslint.configs[nameInCamelCase]) {
        throw new Error(
          `The config name "${name}" is not supported in "extends". Please use "${nameInCamelCase}" instead.`
        );
      }
      throw new Error(`Unknown config name in "extends": ${name}.`);
    }
  }
  configureVueProject({
    scriptLangs: Object.keys(supportedScriptLangs).filter(
      (lang) => supportedScriptLangs[lang]
    ),
    rootDir
  });
  return defineConfigWithVueTs(
    ...configNamesToExtend.map(
      (name) => vueTsConfigs[name]
    )
  );
}

const defineConfig = defineConfigWithVueTs;

export { configureVueProject, createConfig, createConfig as default, defineConfig, defineConfigWithVueTs, vueTsConfigs, withVueTs };
