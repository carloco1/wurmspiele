/**
 * DocuFish Agent Simulation — lokale Demo
 *
 * Simuliert den kompletten Pipeline-Durchlauf mit einem gefakten Jira-Ticket
 * und realistischen (aber gemockten) LLM-Antworten.
 *
 * Kein API-Key nötig.
 *
 * Run: node tests/simulate.js
 */

// ---------------------------------------------------------------------------
// Mock-Jira-Ticket
// ---------------------------------------------------------------------------
const MOCK_TICKET = {
  key: "PROJ-137",
  fields: {
    summary: "Passwort-Reset per E-Mail implementieren",
    description: `
Nutzer können ihr Passwort aktuell nicht zurücksetzen.
Implementiere einen sicheren Passwort-Reset-Flow:
1. Nutzer gibt E-Mail-Adresse ein
2. System sendet einen Reset-Link (gültig 15 Minuten)
3. Nutzer klickt Link → Eingabe neues Passwort
4. Token wird nach Nutzung invalidiert
    `.trim(),
    customfield_acceptance_criteria: `
- Reset-Link läuft nach 15 Minuten ab
- Token kann nur einmal verwendet werden
- Altes Passwort bleibt gültig bis Reset abgeschlossen
- Bei unbekannter E-Mail: keine Fehlermeldung (Security)
- Rate Limiting: max 3 Reset-Anfragen pro Stunde pro E-Mail
    `.trim(),
  },
};

// ---------------------------------------------------------------------------
// Realistische Mock-Agenten-Antworten
// ---------------------------------------------------------------------------
const MOCK_AGENT_RESPONSES = {
  junior_dev: {
    gaps: [
      "Nicht dokumentiert: Was passiert wenn der Nutzer mehrfach Reset anfordert?",
      "Fehlt: Welches E-Mail-Template wird verwendet?",
      "Unklar: Wird der Nutzer nach erfolgreichem Reset automatisch eingeloggt?",
    ],
    suggested_sections: ["Übersicht", "Schritt-für-Schritt Flow", "Fehlerfälle", "FAQ"],
    questions: [
      "Muss der Nutzer eingeloggt sein um den Reset anzufordern?",
      "Was ist die minimale Passwortlänge?",
      "Gibt es eine Bestätigungs-E-Mail nach erfolgreichem Reset?",
    ],
  },
  architect: {
    gaps: [
      "Token-Speicherung nicht spezifiziert (DB vs. Cache/Redis)?",
      "Kein Hinweis auf HTTPS-Pflicht für Reset-Links",
      "Fehlende Definition des Token-Formats (JWT vs. Random UUID?)",
    ],
    suggested_sections: ["Technisches Design", "Security-Überlegungen", "API Endpoints", "Datenbankschema"],
    architecture_notes: [
      "Token sollte als kryptographisch sicherer Zufallswert (crypto.randomBytes) generiert werden",
      "Hashed Token in DB speichern, nie den Klartext",
      "Rate Limiting sollte auf IP UND E-Mail-Adresse angewendet werden",
    ],
  },
  product_manager: {
    gaps: [
      "Kein Hinweis auf Rollout-Plan (Feature Flag?)",
      "Fehlende Nutzer-Kommunikation: Was sieht der Nutzer bei abgelaufenem Link?",
    ],
    suggested_sections: ["Business Context", "Nutzer-Impact", "Deployment Notes"],
    business_notes: [
      "Direkt verbunden mit Support-Tickets über vergessene Passwörter (aktuell 23% aller Support-Anfragen)",
      "Betrifft alle ~12.000 aktiven Nutzer",
      "DSGVO-relevant: E-Mail-Adressen werden temporär verarbeitet",
    ],
  },
};

// ---------------------------------------------------------------------------
// Realistischer Mock-Doc-Output (Confluence Storage Format)
// ---------------------------------------------------------------------------
const MOCK_DOC_OUTPUT = `
<h2>Übersicht</h2>
<p>Dieses Dokument beschreibt den sicheren Passwort-Reset-Flow für <strong>PROJ-137</strong>.
Der Flow erlaubt Nutzern, ihr Passwort via E-Mail zurückzusetzen ohne Support-Kontakt.</p>

<ac:structured-macro ac:name="info">
  <ac:parameter ac:name="title">Business Impact</ac:parameter>
  <ac:rich-text-body>
    <p>Betrifft alle <strong>~12.000 aktiven Nutzer</strong>. Adressiert 23% aller Support-Tickets.</p>
  </ac:rich-text-body>
</ac:structured-macro>

<h2>Schritt-für-Schritt Flow</h2>
<ol>
  <li>Nutzer gibt E-Mail-Adresse auf <code>/reset-password</code> ein</li>
  <li>System prüft ob E-Mail existiert (gibt <strong>keine</strong> Fehlermeldung bei unbekannter Adresse)</li>
  <li>Kryptographisch sicherer Token (UUID v4) wird generiert und <em>gehashed</em> in DB gespeichert</li>
  <li>Reset-Link (<code>https://app.example.com/reset?token=...</code>) per E-Mail versendet — gültig <strong>15 Minuten</strong></li>
  <li>Nutzer klickt Link → gibt neues Passwort ein (min. 8 Zeichen)</li>
  <li>Token wird nach einmaliger Nutzung invalidiert</li>
</ol>

<h2>API Endpoints</h2>
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">text</ac:parameter>
  <ac:rich-text-body>
POST /api/auth/reset-request   { email: string }
POST /api/auth/reset-confirm   { token: string, newPassword: string }
  </ac:rich-text-body>
</ac:structured-macro>

<h2>Security-Überlegungen</h2>
<ul>
  <li>Token als <code>crypto.randomBytes(32)</code> generieren, SHA-256 Hash in DB</li>
  <li>Rate Limiting: max 3 Anfragen/Stunde pro E-Mail UND IP</li>
  <li>Reset-Links nur über HTTPS</li>
  <li>DSGVO: E-Mail-Adresse wird nur für den Reset-Prozess verarbeitet</li>
</ul>

<h2>Fehlerfälle</h2>
<table>
  <tr><th>Szenario</th><th>Nutzer sieht</th></tr>
  <tr><td>Unbekannte E-Mail</td><td>"Wenn die E-Mail registriert ist, erhältst du einen Link" (kein Unterschied)</td></tr>
  <tr><td>Abgelaufener Token</td><td>"Dieser Link ist nicht mehr gültig. Bitte fordere einen neuen an."</td></tr>
  <tr><td>Bereits genutzter Token</td><td>"Dieser Link wurde bereits verwendet."</td></tr>
  <tr><td>Rate Limit erreicht</td><td>"Zu viele Anfragen. Bitte warte 1 Stunde."</td></tr>
</table>

<h2>Deployment Notes</h2>
<ul>
  <li>DB-Migration: neue Tabelle <code>password_reset_tokens</code> (token_hash, user_id, expires_at, used_at)</li>
  <li>Empfehlung: Feature Flag für schrittweisen Rollout</li>
  <li>E-Mail-Template muss vor Deploy in Mail-Service hinterlegt werden</li>
</ul>
`.trim();

// ---------------------------------------------------------------------------
// Simulation Runner
// ---------------------------------------------------------------------------

function printSection(title) {
  console.log("\n" + "=".repeat(60));
  console.log(` ${title}`);
  console.log("=".repeat(60));
}

function printSubSection(title) {
  console.log(`\n--- ${title} ---`);
}

async function simulate() {
  printSection("DocuFish — Agent Simulation (Mock)");

  // Step 0: Ticket
  printSection("JIRA TICKET");
  console.log(`Key:    ${MOCK_TICKET.key}`);
  console.log(`Title:  ${MOCK_TICKET.fields.summary}`);
  console.log(`\nDescription:\n${MOCK_TICKET.fields.description}`);
  console.log(`\nAcceptance Criteria:\n${MOCK_TICKET.fields.customfield_acceptance_criteria}`);

  // Step 1: Simulate 3 agents
  printSection("SCHRITT 1: MIROFISH AGENTEN-SIMULATION");

  const personas = [
    { id: "junior_dev",      name: "Junior Developer" },
    { id: "architect",       name: "Software Architect" },
    { id: "product_manager", name: "Product Manager" },
  ];

  for (const persona of personas) {
    printSubSection(`Agent: ${persona.name}`);
    const response = MOCK_AGENT_RESPONSES[persona.id];

    console.log("Gefundene Lücken:");
    response.gaps.forEach((g) => console.log(`  • ${g}`));

    if (response.questions) {
      console.log("Fragen:");
      response.questions.forEach((q) => console.log(`  ? ${q}`));
    }
    if (response.architecture_notes) {
      console.log("Architektur-Notizen:");
      response.architecture_notes.forEach((n) => console.log(`  ⚙ ${n}`));
    }
    if (response.business_notes) {
      console.log("Business-Kontext:");
      response.business_notes.forEach((n) => console.log(`  $ ${n}`));
    }
  }

  // Step 2: Aggregation
  printSection("SCHRITT 2: AGGREGIERTES FEEDBACK");

  const allGaps = [
    ...new Set([
      ...MOCK_AGENT_RESPONSES.junior_dev.gaps,
      ...MOCK_AGENT_RESPONSES.architect.gaps,
      ...MOCK_AGENT_RESPONSES.product_manager.gaps,
    ]),
  ];

  const allSections = [
    ...new Set([
      ...MOCK_AGENT_RESPONSES.junior_dev.suggested_sections,
      ...MOCK_AGENT_RESPONSES.architect.suggested_sections,
      ...MOCK_AGENT_RESPONSES.product_manager.suggested_sections,
    ]),
  ];

  console.log(`\nGesamt Lücken gefunden: ${allGaps.length}`);
  allGaps.forEach((g, i) => console.log(`  ${i + 1}. ${g}`));

  console.log(`\nVorgeschlagene Sections: ${allSections.join(", ")}`);

  // Step 3: Doc generation
  printSection("SCHRITT 3: GENERIERTE CONFLUENCE SEITE");
  console.log(`\nSeitenname: [DocuFish] ${MOCK_TICKET.fields.summary}`);
  console.log(`Space: ENG\n`);
  console.log(MOCK_DOC_OUTPUT);

  // Summary
  printSection("ZUSAMMENFASSUNG");
  console.log(`  Ticket:       ${MOCK_TICKET.key} — ${MOCK_TICKET.fields.summary}`);
  console.log(`  Agenten:      3 (Junior Dev, Architect, PM)`);
  console.log(`  Lücken:       ${allGaps.length} gefunden und adressiert`);
  console.log(`  Doc Länge:    ${MOCK_DOC_OUTPUT.length} Zeichen`);
  console.log(`  Status:       ✓ Confluence-Seite würde erstellt werden`);
  console.log("");
}

simulate().catch(console.error);
