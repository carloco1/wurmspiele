/**
 * Forge Trigger: fires when a Jira issue is updated.
 * If the transition is to "Done" (or a configured status),
 * automatically kicks off DocuFish documentation generation.
 */

const { storage } = require("@forge/api");
const { simulateAgents } = require("../services/mirofish");
const { generateDoc } = require("../services/docGenerator");
const { upsertPage } = require("../services/confluence");

const TRIGGER_STATUSES = ["Done", "Closed", "Released"];

exports.handler = async (event) => {
  const { issue, changelog } = event;

  // Only act on status transitions to a "done" state
  const statusChange = changelog?.items?.find((i) => i.field === "status");
  if (!statusChange || !TRIGGER_STATUSES.includes(statusChange.toString)) {
    // Check toString value
    const toStatus = statusChange?.toString;
    if (!toStatus || !TRIGGER_STATUSES.includes(toStatus)) {
      return;
    }
  }

  // Read app config from Forge storage (set via the panel UI)
  const apiKey = await storage.getSecret("llm_api_key");
  const llmBaseUrl = (await storage.get("llm_base_url")) || "https://api.openai.com/v1";
  const spaceKey = await storage.get("confluence_space_key");

  if (!apiKey || !spaceKey) {
    console.warn("DocuFish: not configured (missing API key or Confluence space). Skipping.");
    return;
  }

  const context = {
    title: issue.fields.summary,
    description: issue.fields.description,
    acceptanceCriteria: issue.fields.customfield_acceptance_criteria,
    prDiff: null, // Could be fetched from Bitbucket/GitHub via additional API call
  };

  try {
    console.log(`DocuFish: generating docs for ${issue.key}…`);

    const feedback = await simulateAgents(context, apiKey, llmBaseUrl);
    const docContent = await generateDoc(issue, feedback, apiKey, llmBaseUrl);
    const pageUrl = await upsertPage(spaceKey, issue.key, issue.fields.summary, docContent);

    console.log(`DocuFish: page created/updated → ${pageUrl}`);

    // Store the result so the issue panel can display it
    await storage.set(`docufish:result:${issue.key}`, {
      pageUrl,
      generatedAt: new Date().toISOString(),
      gapsFound: feedback.gaps?.length ?? 0,
    });
  } catch (err) {
    console.error(`DocuFish error for ${issue.key}:`, err);
  }
};
