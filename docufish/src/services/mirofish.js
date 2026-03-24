/**
 * MiroFish Multi-Agent Simulation Client
 *
 * Simulates three developer personas to identify gaps in documentation
 * and generate well-rounded Confluence pages.
 *
 *   Persona 1: Junior Developer  → catches missing context / jargon
 *   Persona 2: Software Architect → validates technical completeness
 *   Persona 3: Product Manager   → ensures business context is present
 */

const PERSONAS = [
  {
    id: "junior_dev",
    name: "Junior Developer",
    systemPrompt: `You are a junior software developer reading a Jira ticket and its implementation notes.
You ask clarifying questions about anything that is unclear, missing setup steps, undocumented
assumptions, or unexplained technical decisions. Return a JSON object:
{
  "gaps": ["...list of missing information"],
  "questions": ["...things a newcomer would ask"],
  "suggested_sections": ["...sections that should exist in the docs"]
}`,
  },
  {
    id: "architect",
    name: "Software Architect",
    systemPrompt: `You are a senior software architect reviewing documentation for technical completeness.
You focus on architecture decisions, data flows, API contracts, security implications, and scalability.
Return a JSON object:
{
  "gaps": ["...missing technical details"],
  "architecture_notes": ["...decisions that must be documented"],
  "suggested_sections": ["...sections a tech doc needs"]
}`,
  },
  {
    id: "product_manager",
    name: "Product Manager",
    systemPrompt: `You are a product manager reading technical documentation.
You focus on business context, user impact, success metrics, rollout plan, and stakeholder information.
Return a JSON object:
{
  "gaps": ["...missing business context"],
  "business_notes": ["...what stakeholders need to know"],
  "suggested_sections": ["...sections for non-technical readers"]
}`,
  },
];

/**
 * Run MiroFish simulation: all three agents analyse the ticket in parallel.
 * @param {object} context - { title, description, acceptanceCriteria, prDiff }
 * @param {string} llmApiKey - OpenAI-compatible API key
 * @param {string} llmBaseUrl - API base URL (default: OpenAI)
 * @returns {Promise<object>} aggregated agent feedback
 */
async function simulateAgents(context, llmApiKey, llmBaseUrl = "https://api.openai.com/v1") {
  const userMessage = buildUserMessage(context);

  const results = await Promise.all(
    PERSONAS.map((persona) => runAgent(persona, userMessage, llmApiKey, llmBaseUrl))
  );

  return aggregateFeedback(results);
}

async function runAgent(persona, userMessage, apiKey, baseUrl) {
  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: persona.systemPrompt },
        { role: "user", content: userMessage },
      ],
      response_format: { type: "json_object" },
      temperature: 0.3,
    }),
  });

  if (!response.ok) {
    throw new Error(`MiroFish agent "${persona.name}" failed: ${response.statusText}`);
  }

  const data = await response.json();
  const content = JSON.parse(data.choices[0].message.content);

  return { personaId: persona.id, personaName: persona.name, ...content };
}

function buildUserMessage({ title, description, acceptanceCriteria, prDiff }) {
  return [
    `## Jira Ticket: ${title}`,
    "",
    `### Description\n${description || "(no description)"}`,
    "",
    acceptanceCriteria
      ? `### Acceptance Criteria\n${acceptanceCriteria}`
      : "",
    "",
    prDiff
      ? `### PR / Code Changes (summary)\n\`\`\`diff\n${prDiff.slice(0, 2000)}\n\`\`\``
      : "",
  ]
    .filter(Boolean)
    .join("\n");
}

function aggregateFeedback(results) {
  const allGaps = [];
  const allSections = new Set();
  const extraNotes = {};

  for (const result of results) {
    allGaps.push(...(result.gaps || []));

    for (const s of result.suggested_sections || []) {
      allSections.add(s);
    }

    // Collect persona-specific notes
    if (result.questions) extraNotes.juniorDevQuestions = result.questions;
    if (result.architecture_notes) extraNotes.architectureNotes = result.architecture_notes;
    if (result.business_notes) extraNotes.businessNotes = result.business_notes;
  }

  return {
    gaps: [...new Set(allGaps)],
    suggestedSections: [...allSections],
    ...extraNotes,
  };
}

module.exports = { simulateAgents };
