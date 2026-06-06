export default {
  testEnvironment: 'node',
  testMatch: ['**/__tests__/**/*.test.js'],
  collectCoverageFrom: [
    'src/referral/**/*.js',
    '!src/referral/**/index.js',
    '!src/referral/**/*.routes.js',
    'src/services/demand-state-machine.service.js',
    'src/services/demand-approval.service.js',
    'src/services/interview-state-machine.service.js',
  ],
  coverageThreshold: {
    'src/referral/services/': { branches: 70, functions: 80, lines: 80, statements: 80 },
    'src/referral/machines/': { branches: 90, functions: 100, lines: 100, statements: 100 },
    'src/services/demand-state-machine.service.js': { branches: 80, functions: 90, lines: 90, statements: 90 },
    'src/services/interview-state-machine.service.js': { branches: 80, functions: 90, lines: 90, statements: 90 },
  },
  moduleFileExtensions: ['js', 'json'],
  transform: {},
};
