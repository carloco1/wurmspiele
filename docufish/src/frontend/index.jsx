/**
 * DocuFish — Jira Issue Panel UI
 * Shows documentation status and allows manual generation.
 */

import ForgeUI, {
  render,
  IssuePanel,
  Fragment,
  Text,
  Button,
  ButtonSet,
  Link,
  Badge,
  SectionMessage,
  Form,
  TextField,
  useProductContext,
  useState,
  useEffect,
  invoke,
} from "@forge/ui";

const App = () => {
  const context = useProductContext();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(async () => {
    const data = await invoke("getDocStatus");
    setStatus(data.result);
  }, []);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    const data = await invoke("generateNow", {});
    setLoading(false);

    if (data.error) {
      setError(data.error);
    } else {
      setStatus(data.result);
    }
  };

  const handleSaveSettings = async (formData) => {
    await invoke("saveSettings", formData);
    setShowSettings(false);
  };

  if (showSettings) {
    return (
      <Fragment>
        <Text>**DocuFish Settings**</Text>
        <Form onSubmit={handleSaveSettings} submitButtonText="Save">
          <TextField
            name="apiKey"
            label="LLM API Key (OpenAI or compatible)"
            placeholder="sk-..."
          />
          <TextField
            name="spaceKey"
            label="Confluence Space Key"
            placeholder="ENG"
          />
          <TextField
            name="llmBaseUrl"
            label="LLM Base URL (optional)"
            placeholder="https://api.openai.com/v1"
          />
        </Form>
        <Button text="Cancel" onClick={() => setShowSettings(false)} />
      </Fragment>
    );
  }

  return (
    <Fragment>
      <Text>**DocuFish Documentation**</Text>

      {error && (
        <SectionMessage title="Error" appearance="error">
          <Text>{error}</Text>
        </SectionMessage>
      )}

      {status ? (
        <Fragment>
          <SectionMessage title="Documentation generated" appearance="confirmation">
            <Text>
              Confluence page created with MiroFish simulation.
              Gaps found: **{status.gapsFound}**
            </Text>
            <Link href={status.pageUrl} openNewTab>
              Open in Confluence
            </Link>
          </SectionMessage>
          <Text>Last generated: {new Date(status.generatedAt).toLocaleString()}</Text>
          <ButtonSet>
            <Button
              text={loading ? "Generating…" : "Regenerate"}
              onClick={handleGenerate}
              disabled={loading}
            />
            <Button text="Settings" onClick={() => setShowSettings(true)} appearance="subtle" />
          </ButtonSet>
        </Fragment>
      ) : (
        <Fragment>
          <Text>
            No documentation generated yet. Click below to run the MiroFish
            multi-agent simulation and create a Confluence page.
          </Text>
          <ButtonSet>
            <Button
              text={loading ? "Generating…" : "Generate Docs"}
              onClick={handleGenerate}
              disabled={loading}
              appearance="primary"
            />
            <Button text="Settings" onClick={() => setShowSettings(true)} appearance="subtle" />
          </ButtonSet>
        </Fragment>
      )}
    </Fragment>
  );
};

export const run = render(
  <IssuePanel>
    <App />
  </IssuePanel>
);
