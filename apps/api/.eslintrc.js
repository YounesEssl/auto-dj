module.exports = {
  root: true,
  extends: ['@autodj/config-eslint/node'],
  parserOptions: {
    project: './tsconfig.json',
    tsconfigRootDir: __dirname,
  },
};
