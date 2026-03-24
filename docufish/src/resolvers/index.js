/**
 * Forge Resolver — handles UI function calls from the issue panel.
 */

const Resolver = require("@forge/resolver");
const { storage } = require("@forge/api");
const { simulateAgents } = require("../services/mirofish");
const { generateDoc } = require("../services/docGenerator");
const { upsertPage } = require("../services/confluence");

const resolver = new Resolver();

// Called when the panel loads — returns existing result if available
resolver.define("getDocStatus", async ({ context }) => {
  const issueKey = context.extension.issue.key;
  const result = await storage.get(`docufish:result:${issueKey}`);
  return { issueKey, result: result || null };
});

// Manually trigger doc generation from the panel
resolver.define("generateNow", async ({ context, payload }) => {
  const issueKey = context.extension.issue.key;

  const apiKey = await storage.getSecret("llm_api_key");
  const llmBaseUrl = (await storage.get("llm_base_url")) || "https://api.openai.com/v1";
  const spaceKey = payload?.spaceKey || (await storage.get("confluence_space_key"));

  if (!apiKey) {
    return { error: "LLM API key not configured. Go to DocuFish settings." };
  }
  if (!spaceKey) {
    return { error: "Confluence space key not configured. Go to DocuFish settings." };
  }

  // Fetch issue details via Jira API
  const { requestJira } = require("@forge/api");
  const issueResp = await requestJira(`/rest/api/3/issue/${issueKey}`, {
    headers: { Accept: "application/json" },
  });
  const issue = await issueResp.json();

  const agentContext = {
    title: issue.fields.summary,
    description: issue.fields.description,
    acceptanceCriteria: issue.fields.customfield_acceptance_criteria,
    prDiff: null,
  };

  try {
    const feedback = await simulateAgents(agentContext, apiKey, llmBaseUrl);
    const docContent = await generateDoc(issue, feedback, apiKey, llmBaseUrl);
    const pageUrl = await upsertPage(spaceKey, issueKey, issue.fields.summary, docContent);

    const result = {
      pageUrl,
      generatedAt: new Date().toISOString(),
      gapsFound: feedback.gaps?.length ?? 0,
    };

    await storage.set(`docufish:result:${issueKey}`, result);
    return { success: true, result };
  } catch (err) {
    return { error: err.message };
  }
});

// Save settings (API key, space key, LLM URL)
resolver.define("saveSettings", async ({ payload }) => {
  const { apiKey, spaceKey, llmBaseUrl } = payload;

  if (apiKey) await storage.setSecret("llm_api_key", apiKey);
  if (spaceKey) await storage.set("confluence_space_key", spaceKey);
  if (llmBaseUrl) await storage.set("llm_base_url", llmBaseUrl);

  return { success: true };
});

exports.handler = resolver.getDefinitions();
