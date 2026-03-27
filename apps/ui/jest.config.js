const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

const customJestConfig = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/tests/setupTests.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testMatch: ['**/tests/**/*.test.(ts|tsx|js)'],
  coverageThreshold: {
    global: {
      branches: 44,
      functions: 49,
      lines: 58,
      statements: 57,
    },
  },
};

module.exports = createJestConfig(customJestConfig);
