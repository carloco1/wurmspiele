/**
 * Unit Tests: docGenerator.js
 */

const { fetch: forgeFetch } = require("./__mocks__/@forge/api");
const { generateDoc } = require("../src/services/docGenerator");

// alias for readability in tests
const fetch = forgeFetch;

const mockIssue = {
  key: "PROJ-42",
  fields: {
    summary: "Add user login endpoint",
    description: "Implement POST /api/login with JWT response",
    customfield_acceptance_criteria: "Returns 200 + token on valid credentials",
  },
};

const mockFeedback = {
  gaps: ["Missing error handling docs", "No rate limiting mentioned"],
  suggestedSections: ["Overview", "API Reference", "Security", "Deployment Notes"],
  juniorDevQuestions: ["What happens on DB failure?"],
  architectureNotes: ["Use RS256 for JWT signing"],
  businessNotes: ["Required for mobile app launch"],
};

const mockDocContent = "<h2>Overview</h2><p>This page documents PROJ-42.</p>";

const mockLLMResponse = (content) => ({
  ok: true,
  json: async () => ({
    choices: [{ message: { content } }],
  }),
});

describe("generateDoc", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("calls LLM once", async () => {
    fetch.mockResolvedValue(mockLLMResponse(mockDocContent));

    await generateDoc(mockIssue, mockFeedback, "test-key");

    expect(fetch).toHaveBeenCalledTimes(1);
  });

  test("returns LLM response content directly", async () => {
    fetch.mockResolvedValue(mockLLMResponse(mockDocContent));

    const result = await generateDoc(mockIssue, mockFeedback, "test-key");

    expect(result).toBe(mockDocContent);
  });

  test("includes issue key in prompt", async () => {
    fetch.mockResolvedValue(mockLLMResponse(mockDocContent));

    await generateDoc(mockIssue, mockFeedback, "test-key");

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    const userMsg = body.messages.find((m) => m.role === "user").content;
    expect(userMsg).toContain("PROJ-42");
  });

  test("includes all feedback gaps in prompt", async () => {
    fetch.mockResolvedValue(mockLLMResponse(mockDocContent));

    await generateDoc(mockIssue, mockFeedback, "test-key");

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    const userMsg = body.messages.find((m) => m.role === "user").content;

    expect(userMsg).toContain("Missing error handling docs");
    expect(userMsg).toContain("No rate limiting mentioned");
  });

  test("includes architecture notes in prompt", async () => {
    fetch.mockResolvedValue(mockLLMResponse(mockDocContent));

    await generateDoc(mockIssue, mockFeedback, "test-key");

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    const userMsg = body.messages.find((m) => m.role === "user").content;
    expect(userMsg).toContain("Use RS256 for JWT signing");
  });

  test("includes business notes in prompt", async () => {
    fetch.mockResolvedValue(mockLLMResponse(mockDocContent));

    await generateDoc(mockIssue, mockFeedback, "test-key");

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    const userMsg = body.messages.find((m) => m.role === "user").content;
    expect(userMsg).toContain("Required for mobile app launch");
  });

  test("uses custom LLM base URL", async () => {
    fetch.mockResolvedValue(mockLLMResponse(mockDocContent));

    await generateDoc(mockIssue, mockFeedback, "key", "https://custom-llm.io/v1");

    const [url] = fetch.mock.calls[0];
    expect(url).toContain("custom-llm.io");
  });

  test("throws on non-ok LLM response", async () => {
    fetch.mockResolvedValue({ ok: false, statusText: "Rate limited" });

    await expect(generateDoc(mockIssue, mockFeedback, "key")).rejects.toThrow(
      "Rate limited"
    );
  });

  test("handles missing acceptance criteria gracefully", async () => {
    fetch.mockResolvedValue(mockLLMResponse(mockDocContent));

    const issueWithoutAC = {
      ...mockIssue,
      fields: { ...mockIssue.fields, customfield_acceptance_criteria: null },
    };

    await expect(generateDoc(issueWithoutAC, mockFeedback, "key")).resolves.toBe(
      mockDocContent
    );
  });

  test("handles empty feedback gracefully", async () => {
    fetch.mockResolvedValue(mockLLMResponse(mockDocContent));

    const emptyFeedback = { gaps: [], suggestedSections: [] };

    await expect(generateDoc(mockIssue, emptyFeedback, "key")).resolves.toBe(
      mockDocContent
    );
  });
});
