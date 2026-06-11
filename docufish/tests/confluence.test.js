/**
 * Unit Tests: confluence.js
 */

// Mock @forge/api before requiring the module
const mockStorageGet = jest.fn();
const mockStorageSet = jest.fn();
const mockRequestConfluence = jest.fn();

jest.mock("@forge/api", () => ({
  requestConfluence: mockRequestConfluence,
  storage: {
    get: mockStorageGet,
    set: mockStorageSet,
  },
}));

const { upsertPage } = require("../src/services/confluence");

const mockJsonResponse = (data, ok = true) => ({
  ok,
  json: async () => data,
});

describe("upsertPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("creates a new page when no existing page is stored", async () => {
    mockStorageGet.mockResolvedValue(null);
    mockRequestConfluence.mockResolvedValue(
      mockJsonResponse({ id: "page-123", _links: { webui: "/wiki/spaces/ENG/pages/page-123" } })
    );

    const url = await upsertPage("ENG", "PROJ-42", "Login Endpoint", "<p>Content</p>");

    expect(mockRequestConfluence).toHaveBeenCalledTimes(1);
    const [endpoint, options] = mockRequestConfluence.mock.calls[0];
    expect(endpoint).toBe("/wiki/rest/api/content");
    expect(options.method).toBe("POST");
  });

  test("saves new page ID to storage after creation", async () => {
    mockStorageGet.mockResolvedValue(null);
    mockRequestConfluence.mockResolvedValue(
      mockJsonResponse({ id: "page-999", _links: { webui: "/wiki/page-999" } })
    );

    await upsertPage("ENG", "PROJ-42", "Title", "<p>Body</p>");

    expect(mockStorageSet).toHaveBeenCalledWith("docufish:page:PROJ-42", "page-999");
  });

  test("returns the page URL after creation", async () => {
    mockStorageGet.mockResolvedValue(null);
    mockRequestConfluence.mockResolvedValue(
      mockJsonResponse({ id: "p1", _links: { webui: "/wiki/spaces/ENG/pages/p1" } })
    );

    const url = await upsertPage("ENG", "PROJ-1", "Title", "<p/>");

    expect(url).toBe("/wiki/spaces/ENG/pages/p1");
  });

  test("updates existing page when page ID is in storage", async () => {
    mockStorageGet.mockResolvedValue("existing-page-id");

    // First call: GET current version
    mockRequestConfluence
      .mockResolvedValueOnce(
        mockJsonResponse({ version: { number: 3 }, _links: {} })
      )
      // Second call: PUT update
      .mockResolvedValueOnce(
        mockJsonResponse({ _links: { webui: "/wiki/page-updated" } })
      );

    await upsertPage("ENG", "PROJ-42", "Updated Title", "<p>New content</p>");

    expect(mockRequestConfluence).toHaveBeenCalledTimes(2);
    const [, putOptions] = mockRequestConfluence.mock.calls[1];
    expect(putOptions.method).toBe("PUT");
  });

  test("increments version number on update", async () => {
    mockStorageGet.mockResolvedValue("page-id");
    mockRequestConfluence
      .mockResolvedValueOnce(mockJsonResponse({ version: { number: 5 }, _links: {} }))
      .mockResolvedValueOnce(mockJsonResponse({ _links: { webui: "/wiki/p" } }));

    await upsertPage("ENG", "PROJ-42", "Title", "<p/>");

    const putBody = JSON.parse(mockRequestConfluence.mock.calls[1][1].body);
    expect(putBody.version.number).toBe(6);
  });

  test("adds DocuFish header to page content", async () => {
    mockStorageGet.mockResolvedValue(null);
    mockRequestConfluence.mockResolvedValue(
      mockJsonResponse({ id: "p1", _links: { webui: "/wiki/p1" } })
    );

    await upsertPage("ENG", "PROJ-42", "Title", "<p>My content</p>");

    const postBody = JSON.parse(mockRequestConfluence.mock.calls[0][1].body);
    const bodyValue = postBody.body.storage.value;

    expect(bodyValue).toContain("DocuFish");
    expect(bodyValue).toContain("PROJ-42");
    expect(bodyValue).toContain("My content");
  });

  test("prefixes page title with [DocuFish]", async () => {
    mockStorageGet.mockResolvedValue(null);
    mockRequestConfluence.mockResolvedValue(
      mockJsonResponse({ id: "p1", _links: { webui: "/wiki/p1" } })
    );

    await upsertPage("ENG", "PROJ-42", "Login Endpoint", "<p/>");

    const postBody = JSON.parse(mockRequestConfluence.mock.calls[0][1].body);
    expect(postBody.title).toBe("[DocuFish] Login Endpoint");
  });

  test("uses correct space key in POST body", async () => {
    mockStorageGet.mockResolvedValue(null);
    mockRequestConfluence.mockResolvedValue(
      mockJsonResponse({ id: "p1", _links: { webui: "/wiki/p1" } })
    );

    await upsertPage("MYSPACE", "PROJ-1", "Title", "<p/>");

    const postBody = JSON.parse(mockRequestConfluence.mock.calls[0][1].body);
    expect(postBody.space.key).toBe("MYSPACE");
  });
});
