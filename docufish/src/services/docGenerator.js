/**
 * Generates a structured Confluence page from a Jira ticket +
 * the aggregated MiroFish multi-agent feedback.
 */

const { fetch } = require("@forge/api");

/**
 * @param {object} ticket   - Jira issue object (summary, description, key, …)
 * @param {object} feedback - Result of mirofish.simulateAgents()
 * @param {string} apiKey   - LLM API key
 * @param {string} baseUrl  - LLM base URL
 * @returns {Promise<string>} Confluence Storage Format (XHTML) content
 */
async function generateDoc(ticket, feedback, apiKey, baseUrl = "https://api.openai.com/v1") {
  const systemPrompt = `You are a technical writer who creates Confluence documentation.
Generate documentation in Confluence Storage Format (XHTML subset).
Use <h2>, <p>, <ul>, <li>, <ac:structured-macro> for code blocks.
Be concise, professional, and developer-friendly.
Always include the following sections if relevant:
Overview, Background, Technical Design, API / Interface Changes,
Acceptance Criteria, Deployment Notes, Open Questions.`;

  const userMessage = buildGeneratorPrompt(ticket, feedback);

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: "gpt-4o",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userMessage },
      ],
      temperature: 0.4,
      max_tokens: 3000,
    }),
  });

  if (!response.ok) {
    throw new Error(`Doc generation failed: ${response.statusText}`);
  }

  const data = await response.json();
  return data.choices[0].message.content;
}

function buildGeneratorPrompt(ticket, feedback) {
  const sections = feedback.suggestedSections?.join(", ") || "";
  const gaps = feedback.gaps?.map((g) => `- ${g}`).join("\n") || "";
  const juniorQ = feedback.juniorDevQuestions?.map((q) => `- ${q}`).join("\n") || "";
  const archNotes = feedback.architectureNotes?.map((n) => `- ${n}`).join("\n") || "";
  const bizNotes = feedback.businessNotes?.map((n) => `- ${n}`).join("\n") || "";

  return `
## Jira Ticket: [${ticket.key}] ${ticket.fields.summary}

### Description
${ticket.fields.description || "(none)"}

### Acceptance Criteria
${ticket.fields.customfield_acceptance_criteria || "(none)"}

---
## MiroFish Agent Feedback

### Sections to include
${sections}

### Identified Gaps (must be addressed in the doc)
${gaps}

### Junior Developer Questions (answer these in the doc)
${juniorQ}

### Architect Notes (include these technical details)
${archNotes}

### Product Manager Notes (include this business context)
${bizNotes}

---
Now generate the full Confluence page in Confluence Storage Format.
Address all identified gaps. Write for a mixed technical/non-technical audience.
`.trim();
}

module.exports = { generateDoc };
