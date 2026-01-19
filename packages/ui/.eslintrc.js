module.exports = {
  root: true,
  extends: ['@autodj/config-eslint/react'],
  parserOptions: {
    project: './tsconfig.json',
    tsconfigRootDir: __dirname,
  },
};
