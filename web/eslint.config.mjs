import nextCoreWebVitals from 'eslint-config-next/core-web-vitals';
import prettier from 'eslint-config-prettier';

/** @type {import('eslint').Linter.Config[]} */
const eslintConfig = [
  ...nextCoreWebVitals,
  prettier,
  {
    // Keep the rule set this app had under `next lint` with Next 15.
    linterOptions: {
      reportUnusedDisableDirectives: 'off',
    },
    rules: {
      // React Compiler rules that eslint-plugin-react-hooks 7 added to its
      // recommended preset. This app does not use the React Compiler.
      'react-hooks/static-components': 'off',
      'react-hooks/use-memo': 'off',
      'react-hooks/preserve-manual-memoization': 'off',
      'react-hooks/incompatible-library': 'off',
      'react-hooks/immutability': 'off',
      'react-hooks/globals': 'off',
      'react-hooks/refs': 'off',
      'react-hooks/set-state-in-effect': 'off',
      'react-hooks/error-boundaries': 'off',
      'react-hooks/purity': 'off',
      'react-hooks/set-state-in-render': 'off',
      'react-hooks/unsupported-syntax': 'off',
      'react-hooks/config': 'off',
      'react-hooks/gating': 'off',
      // New in the Next 16 core-web-vitals preset.
      '@next/next/no-location-assign-relative-destination': 'off',
    },
  },
];

export default eslintConfig;
