/**
 * Integration Test: Full DocuFish pipeline
 *
 * Runs a real end-to-end flow against a live LLM API:
 *   Jira context → MiroFish simulation → Doc generation
 *
 * Requires environment variables:
 *   LLM_API_KEY   — OpenAI-compatible API key (required)
 *   LLM_BASE_URL  — API base URL (optional, default: OpenAI)
 *   LLM_MODEL     — model override (optional)
 *
 * Run with:
 *   LLM_API_KEY=sk-... npx jest tests/integration
 *
 * Skipped automatically if LLM_API_KEY is not set.
 */

const { simulateAgents } = require("../../src/services/mirofish");
const { generateDoc } = require("../../src/services/docGenerator");

const API_KEY = process.env.LLM_API_KEY;
const BASE_URL = process.env.LLM_BASE_URL || "https://api.openai.com/v1";

const skipIfNoKey = API_KEY ? describe : describe.skip;

const mockIssue = {
  key: "PROJ-99",
  fields: {
    summary: "Add rate limiting to the login endpoint",
    description:
      "The POST /api/login endpoint has no rate limiting. " +
      "Implement a sliding window rate limiter: max 5 attempts per IP per minute. " +
      "Return HTTP 429 with Retry-After header when limit is exceeded.",
    customfield_acceptance_criteria:
      "- Returns 429 after 5 failed attempts within 60 seconds\n" +
      "- Retry-After header is set correctly\n" +
      "- Successful logins do not count toward the limit\n" +
      "- Limit resets after 60 seconds",
    prDiff: null,
  },
};

skipIfNoKey("DocuFish integration — real LLM", () => {
  jest.setTimeout(60_000); // LLM calls can be slow

  let agentFeedback;

  describe("Step 1: MiroFish agent simulation", () => {
    beforeAll(async () => {
      agentFeedback = await simulateAgents(
        {
          title: mockIssue.fields.summary,
          description: mockIssue.fields.description,
          acceptanceCriteria: mockIssue.fields.customfield_acceptance_criteria,
          prDiff: null,
        },
        API_KEY,
        BASE_URL
      );
    });

    test("returns an object with gaps array", () => {
      expect(agentFeedback).toHaveProperty("gaps");
      expect(Array.isArray(agentFeedback.gaps)).toBe(true);
    });

    test("finds at least one gap", () => {
      expect(agentFeedback.gaps.length).toBeGreaterThan(0);
      console.log("\nGaps found by agents:");
      agentFeedback.gaps.forEach((g) => console.log(" •", g));
    });

    test("returns suggested sections", () => {
      expect(Array.isArray(agentFeedback.suggestedSections)).toBe(true);
      expect(agentFeedback.suggestedSections.length).toBeGreaterThan(0);
      console.log("\nSuggested sections:");
      agentFeedback.suggestedSections.forEach((s) => console.log(" •", s));
    });

    test("junior dev questions are present", () => {
      expect(Array.isArray(agentFeedback.juniorDevQuestions)).toBe(true);
      expect(agentFeedback.juniorDevQuestions.length).toBeGreaterThan(0);
    });

    test("architecture notes are present", () => {
      expect(Array.isArray(agentFeedback.architectureNotes)).toBe(true);
      expect(agentFeedback.architectureNotes.length).toBeGreaterThan(0);
    });

    test("business notes are present", () => {
      expect(Array.isArray(agentFeedback.businessNotes)).toBe(true);
      expect(agentFeedback.businessNotes.length).toBeGreaterThan(0);
    });
  });

  describe("Step 2: Doc generation", () => {
    let docContent;

    beforeAll(async () => {
      // Ensure feedback is available (runs after Step 1)
      if (!agentFeedback) {
        agentFeedback = await simulateAgents(
          {
            title: mockIssue.fields.summary,
            description: mockIssue.fields.description,
            acceptanceCriteria: mockIssue.fields.customfield_acceptance_criteria,
            prDiff: null,
          },
          API_KEY,
          BASE_URL
        );
      }

      docContent = await generateDoc(mockIssue, agentFeedback, API_KEY, BASE_URL);
    });

    test("returns a non-empty string", () => {
      expect(typeof docContent).toBe("string");
      expect(docContent.length).toBeGreaterThan(200);
    });

    test("contains basic Confluence markup", () => {
      expect(docContent).toMatch(/<h[1-6]>|<p>|<ul>/);
    });

    test("mentions the issue key", () => {
      expect(docContent).toContain("PROJ-99");
    });

    test("addresses at least one gap from agent feedback", () => {
      const firstGap = agentFeedback.gaps[0];
      // The gap topic (first significant word) should appear somewhere in the doc
      const keyword = firstGap.split(" ").find((w) => w.length > 4);
      expect(docContent.toLowerCase()).toContain(keyword.toLowerCase());
    });

    test("has reasonable length (not truncated)", () => {
      // A real Confluence doc should be at least 500 chars
      expect(docContent.length).toBeGreaterThan(500);
      console.log(`\nGenerated doc length: ${docContent.length} chars`);
      console.log("\nDoc preview (first 400 chars):");
      console.log(docContent.slice(0, 400));
    });
  });
});

// Always-run smoke test — no API key needed
describe("DocuFish integration — smoke (no API key)", () => {
  test("simulateAgents rejects immediately with invalid key", async () => {
    await expect(
      simulateAgents(
        { title: "Test", description: "Test", acceptanceCriteria: null, prDiff: null },
        "invalid-key-xyz"
      )
    ).rejects.toThrow();
  });
});
