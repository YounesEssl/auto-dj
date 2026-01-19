module.exports = {
  root: true,
  extends: ['@autodj/config-eslint'],
  parserOptions: {
    project: './tsconfig.json',
    tsconfigRootDir: __dirname,
  },
};
