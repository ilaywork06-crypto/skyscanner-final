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
    },
  },
)
