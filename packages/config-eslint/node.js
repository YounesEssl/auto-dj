/**
 * ESLint configuration for Node.js/NestJS applications
 * @type {import('eslint').Linter.Config}
 */
module.exports = {
  extends: ['./index.js'],
  rules: {
    '@typescript-eslint/interface-name-prefix': 'off',
    '@typescript-eslint/explicit-function-return-type': 'off',
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    '@typescript-eslint/no-explicit-any': 'warn',
    'no-console': 'off',
  },
  env: {
    node: true,
    es2022: true,
    jest: true,
  },
};
