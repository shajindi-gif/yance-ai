import { defineConfig, globalIgnores } from 'eslint/config'
import nextVitals from 'eslint-config-next/core-web-vitals'
import nextTs from 'eslint-config-next/typescript'

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // ACC-20 follow-up: 19 existing pages load data with the common
      // "setState inside useEffect on mount" pattern. Rewriting them all is a
      // behavioural change across the app, so this new rule starts as a warning
      // and is tracked for a dedicated refactor. Raise it to "error" afterwards.
      'react-hooks/set-state-in-effect': 'warn',
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    '.next/**',
    'out/**',
    'build/**',
    'next-env.d.ts',
    // Playwright artefacts.
    'playwright-report/**',
    'test-results/**',
  ]),
])

export default eslintConfig
