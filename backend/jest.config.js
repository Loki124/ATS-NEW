export default {
  testEnvironment: 'node',
  testMatch: ['**/__tests__/**/*.test.js'],
  collectCoverageFrom: [
    'src/referral/**/*.js',
    '!src/referral/**/index.js',
    '!src/referral/**/*.routes.js',
  ],
  coverageThreshold: {
    'src/referral/services/': { branches: 70, functions: 80, lines: 80, statements: 80 },
    'src/referral/machines/': { branches: 90, functions: 100, lines: 100, statements: 100 },
  },
  moduleFileExtensions: ['js', 'json'],
  transform: {},
};
