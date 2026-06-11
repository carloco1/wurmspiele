/**
 * Manual mock for @forge/api
 * Used by Jest when running outside the Forge runtime.
 */

const fetch = jest.fn();
const requestConfluence = jest.fn();
const requestJira = jest.fn();

const storage = {
  get: jest.fn(),
  set: jest.fn(),
  getSecret: jest.fn(),
  setSecret: jest.fn(),
};

module.exports = { fetch, requestConfluence, requestJira, storage };
