/**
 * Unit Tests: mirofish.js
 */

const { simulateAgents } = require("../src/services/mirofish");

// Mock global fetch
global.fetch = jest.fn();

const mockLLMResponse = (content) => ({
  ok: true,
  json: async () => ({
    choices: [{ message: { content: JSON.stringify(content) } }],
  }),
});

describe("simulateAgents", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const context = {
    title: "Add user login endpoint",
    description: "Implement POST /api/login with JWT response",
    acceptanceCriteria: "Returns 200 + token on success, 401 on failure",
    prDiff: null,
  };

  test("calls LLM once per persona (3 total)", async () => {
    fetch.mockResolvedValue(
      mockLLMResponse({ gaps: [], suggested_sections: [], questions: [] })
    );

    await simulateAgents(context, "test-key");

    expect(fetch).toHaveBeenCalledTimes(3);
  });

  test("sends correct Authorization header", async () => {
    fetch.mockResolvedValue(
      mockLLMResponse({ gaps: [], suggested_sections: [] })
    );

    await simulateAgents(context, "sk-testkey123");

    const [, options] = fetch.mock.calls[0];
    expect(options.headers["Authorization"]).toBe("Bearer sk-testkey123");
  });

  test("uses custom LLM base URL", async () => {
    fetch.mockResolvedValue(
      mockLLMResponse({ gaps: [], suggested_sections: [] })
    );

    await simulateAgents(context, "key", "https://my-llm.example.com/v1");

    const [url] = fetch.mock.calls[0];
    expect(url).toContain("my-llm.example.com");
  });

  test("aggregates gaps from all 3 agents", async () => {
    fetch
      .mockResolvedValueOnce(
        mockLLMResponse({
          gaps: ["Missing error handling docs"],
          suggested_sections: ["Error Codes"],
          questions: ["What happens on DB failure?"],
        })
      )
      .mockResolvedValueOnce(
        mockLLMResponse({
          gaps: ["No rate limiting mentioned"],
          suggested_sections: ["Security"],
          architecture_notes: ["JWT expiry should be documented"],
        })
      )
      .mockResolvedValueOnce(
        mockLLMResponse({
          gaps: ["No rollout plan"],
          suggested_sections: ["Deployment Notes"],
          business_notes: ["Affects all mobile users"],
        })
      );

    const result = await simulateAgents(context, "key");

    expect(result.gaps).toContain("Missing error handling docs");
    expect(result.gaps).toContain("No rate limiting mentioned");
    expect(result.gaps).toContain("No rollout plan");
    expect(result.gaps).toHaveLength(3);
  });

  test("deduplicates identical gaps across agents", async () => {
    const sameGap = "Missing authentication details";
    fetch.mockResolvedValue(
      mockLLMResponse({ gaps: [sameGap], suggested_sections: [] })
    );

    const result = await simulateAgents(context, "key");

    const count = result.gaps.filter((g) => g === sameGap).length;
    expect(count).toBe(1);
  });

  test("aggregates suggestedSections without duplicates", async () => {
    fetch
      .mockResolvedValueOnce(
        mockLLMResponse({ gaps: [], suggested_sections: ["Overview", "API Reference"] })
      )
      .mockResolvedValueOnce(
        mockLLMResponse({ gaps: [], suggested_sections: ["Overview", "Security"] })
      )
      .mockResolvedValueOnce(
        mockLLMResponse({ gaps: [], suggested_sections: ["Deployment Notes"] })
      );

    const result = await simulateAgents(context, "key");

    expect(result.suggestedSections).toContain("Overview");
    expect(result.suggestedSections.filter((s) => s === "Overview")).toHaveLength(1);
    expect(result.suggestedSections).toContain("Security");
    expect(result.suggestedSections).toContain("Deployment Notes");
  });

  test("includes persona-specific notes in result", async () => {
    fetch
      .mockResolvedValueOnce(
        mockLLMResponse({ gaps: [], suggested_sections: [], questions: ["How does session expire?"] })
      )
      .mockResolvedValueOnce(
        mockLLMResponse({ gaps: [], suggested_sections: [], architecture_notes: ["Use RS256 for JWT"] })
      )
      .mockResolvedValueOnce(
        mockLLMResponse({ gaps: [], suggested_sections: [], business_notes: ["Needed for GDPR compliance"] })
      );

    const result = await simulateAgents(context, "key");

    expect(result.juniorDevQuestions).toEqual(["How does session expire?"]);
    expect(result.architectureNotes).toEqual(["Use RS256 for JWT"]);
    expect(result.businessNotes).toEqual(["Needed for GDPR compliance"]);
  });

  test("throws if LLM returns non-ok response", async () => {
    fetch.mockResolvedValue({ ok: false, statusText: "Unauthorized" });

    await expect(simulateAgents(context, "bad-key")).rejects.toThrow("Unauthorized");
  });

  test("includes PR diff in user message when provided", async () => {
    fetch.mockResolvedValue(
      mockLLMResponse({ gaps: [], suggested_sections: [] })
    );

    await simulateAgents({ ...context, prDiff: "- old line\n+ new line" }, "key");

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    const userMsg = body.messages.find((m) => m.role === "user").content;
    expect(userMsg).toContain("old line");
  });
});
