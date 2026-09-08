/**
 * The lint rules of the web client, combining the recommended Vue and TypeScript sets with the house rules.
 */

import eslint from '@eslint/js'
import vueTypeScript from '@vue/eslint-config-typescript'
import vue from 'eslint-plugin-vue'
import typescriptEslint from 'typescript-eslint'

export default typescriptEslint.config(
  { ignores: ['dist/**', 'node_modules/**', 'src/typed-router.d.ts'] },
  eslint.configs.recommended,
  ...typescriptEslint.configs.recommended,
  ...vue.configs['flat/recommended'],
  ...vueTypeScript(),
  {
    rules: {
      eqeqeq: ['error', 'always'],
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],
      'vue/multi-word-component-names': 'off',
      'vue/component-tags-order': ['error', { order: ['template', 'script', 'style'] }],
      'vue/block-order': ['error', { order: ['template', 'script', 'style'] }],
      'vue/no-v-html': 'off',
      /*
       * A component used in a template but never imported is neither a build error nor a type error: the
       * compiler emits a runtime lookup, the lookup finds nothing, and the element renders as nothing at
       * all. That is how four dialogs came to raise a confirmation nobody could see, and it stayed
       * invisible to every other check here. This rule is the one that sees it.
       *
       * Vuetify's own components are registered on the application rather than imported, so they are
       * genuinely undefined as far as this rule can tell and are named out of it. Everything else has to be
       * imported where it is used.
       */
      'vue/no-undef-components': ['error', { ignorePatterns: ['^v-', '^router-'] }],
    },
  },
)
