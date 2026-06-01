# Memory Multiplayer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Erweitert `memory.html` um Mehrspielermodus (2–6 Spieler) mit Geschlechtsauswahl, rundenbasiertem Turnsystem und Gewinner-Rangliste.

**Architecture:** Alle Änderungen erfolgen in der einzigen `memory.html`. Zwei neue HTML-Screens (`screen-setup`, `screen-difficulty`) werden eingefügt. Der `state` wird um `players[]` und `currentPlayerIndex` erweitert. Neue JS-Funktionen steuern den Setup-Flow und die Turnsystem-Logik. Bestehende Funktionen (`startGame`, `checkMatch`, `showWin`, `resetToStart`) werden angepasst.

**Tech Stack:** Vanilla HTML5, CSS3, Vanilla JavaScript ES6 — keine neuen Abhängigkeiten.

---

## Dateistruktur

```
wurmspiele/
└── memory.html   ← einzige Datei, alle Änderungen hier
```

---

### Task 1: CSS — Badges, Setup, Gewinn-Screen

**Files:**
- Modify: `memory.html` — CSS am Ende des `<style>`-Blocks hinzufügen

- [ ] **Schritt 1: CSS an das Ende des `<style>`-Blocks hinzufügen (vor `</style>`)**

```css
/* Setup-Screen */
.setup-step { display: none; }
.setup-step.active { display: block; }

.player-count-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.name-input {
  font-size: 1.2rem;
  padding: 10px 16px;
  border: 3px solid #ddd;
  border-radius: 12px;
  text-align: center;
  width: 220px;
  margin-bottom: 8px;
  display: block;
  margin-left: auto;
  margin-right: auto;
}
.name-input:focus { outline: none; border-color: #42a5f5; }
.name-input.error { border-color: #ef5350; }

.gender-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 16px;
}

.btn-boy  { background: #42a5f5; color: #fff; }
.btn-girl { background: #e91e8c; color: #fff; }

/* Spielfeld — Spieler-Badges */
.player-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.player-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 20px;
  background: #ddd;
  color: #666;
  font-weight: bold;
  font-size: 0.9rem;
  transition: transform 0.2s, background 0.2s, color 0.2s;
}

.player-badge.active {
  color: #fff;
  transform: scale(1.05);
}

/* Gewinn-Screen */
.winner-name {
  font-size: 2rem;
  font-weight: bold;
  margin: 12px 0;
  animation: pulse 0.8s ease-in-out infinite alternate;
}

@keyframes pulse {
  from { transform: scale(1);    }
  to   { transform: scale(1.08); }
}

.ranking-list {
  list-style: none;
  margin: 16px 0 24px;
  text-align: left;
  display: inline-block;
}

.ranking-list li { font-size: 1.2rem; padding: 6px 0; }
```

- [ ] **Schritt 2: Im Browser prüfen**

`memory.html` öffnen. Erwartetes Ergebnis: Keine CSS-Fehler in der Konsole, das Spiel sieht noch identisch aus.

- [ ] **Schritt 3: Commit**

```bash
cd "c:/Workspace/Software/Games/wurmspiele"
git add memory.html
git commit -m "feat: add multiplayer CSS for badges, setup, and win screen"
```

---

### Task 2: HTML — Screens aktualisieren

**Files:**
- Modify: `memory.html` — screen-start, screen-game, screen-win anpassen + screen-setup und screen-difficulty hinzufügen

- [ ] **Schritt 1: screen-start vereinfachen**

Den kompletten `<div id="screen-start" ...>` Block ersetzen durch:

```html
  <!-- Startbildschirm -->
  <div id="screen-start" class="screen active">
    <h1>🧠 Memory</h1>
    <p>Das klassische Kartenspiel für die ganze Familie!</p>
    <div class="difficulty-buttons">
      <button onclick="showScreen('screen-setup')" class="btn btn-easy">🎮 Los geht's!</button>
    </div>
  </div>
```

- [ ] **Schritt 2: screen-setup nach screen-start einfügen**

Direkt nach `</div>` von screen-start einfügen:

```html
  <!-- Setup-Screen -->
  <div id="screen-setup" class="screen">
    <div id="setup-step1" class="setup-step active">
      <h1>👥 Spieler</h1>
      <p>Wie viele Spieler spielen mit?</p>
      <div class="player-count-buttons">
        <button onclick="selectPlayerCount(2)" class="btn btn-medium">2</button>
        <button onclick="selectPlayerCount(3)" class="btn btn-medium">3</button>
        <button onclick="selectPlayerCount(4)" class="btn btn-medium">4</button>
        <button onclick="selectPlayerCount(5)" class="btn btn-medium">5</button>
        <button onclick="selectPlayerCount(6)" class="btn btn-medium">6</button>
      </div>
    </div>
    <div id="setup-step2" class="setup-step">
      <h1 id="setup-player-title">Spieler 1 einrichten</h1>
      <p>Wie heißt du?</p>
      <input id="player-name-input" class="name-input" type="text" maxlength="12" placeholder="Name eingeben" />
      <p>Bist du ein...?</p>
      <div class="gender-buttons">
        <button onclick="selectGender('boy')"  class="btn btn-boy">👦 Junge</button>
        <button onclick="selectGender('girl')" class="btn btn-girl">👧 Mädchen</button>
      </div>
    </div>
  </div>
```

- [ ] **Schritt 3: screen-difficulty nach screen-setup einfügen**

Direkt nach `</div>` von screen-setup einfügen:

```html
  <!-- Schwierigkeits-Screen -->
  <div id="screen-difficulty" class="screen">
    <h1>🧠 Memory</h1>
    <p>Wähle eine Schwierigkeitsstufe:</p>
    <div class="difficulty-buttons">
      <button onclick="startGame(8, 4, 4)"  class="btn btn-easy">🌱 Leicht<br><small>8 Paare · 4×4</small></button>
      <button onclick="startGame(12, 4, 6)" class="btn btn-medium">🌿 Mittel<br><small>12 Paare · 4×6</small></button>
      <button onclick="startGame(18, 6, 6)" class="btn btn-hard">🌳 Schwer<br><small>18 Paare · 6×6</small></button>
    </div>
  </div>
```

- [ ] **Schritt 4: game-header aktualisieren — player-badges hinzufügen**

Den bestehenden `<div class="game-header">` Block ersetzen durch:

```html
    <div class="game-header">
      <div id="player-badges" class="player-badges"></div>
      <span id="move-counter">Züge: 0</span>
      <button onclick="resetToStart()" class="btn btn-small">↩ Neu</button>
    </div>
```

- [ ] **Schritt 5: screen-win aktualisieren — winner-display und ranking-list**

Den kompletten `<div id="screen-win" ...>` Block ersetzen durch:

```html
  <!-- Gewinn-Screen -->
  <div id="screen-win" class="screen">
    <div class="win-box">
      <div class="confetti">🎉🏆🎉</div>
      <div id="winner-display"></div>
      <ul id="ranking-list" class="ranking-list"></ul>
      <button onclick="resetToStart()" class="btn btn-easy">🔄 Nochmal spielen</button>
    </div>
  </div>
```

- [ ] **Schritt 6: Im Browser prüfen**

Seite laden. Erwartetes Ergebnis: Startbildschirm zeigt nur den "Los geht's!" Button. Kein JS-Fehler in der Konsole.

- [ ] **Schritt 7: Commit**

```bash
git add memory.html
git commit -m "feat: add setup and difficulty screens, update game header and win screen HTML"
```

---

### Task 3: JS — state erweitern + Setup-Funktionen

**Files:**
- Modify: `memory.html` — state erweitern, Setup-Variablen und Setup-Funktionen nach `resetToStart` einfügen

- [ ] **Schritt 1: state-Objekt um players und currentPlayerIndex erweitern**

Den bestehenden `state`-Block ersetzen durch:

```javascript
    const state = {
      moves: 0,
      flippedCards: [],
      matchedPairs: 0,
      totalPairs: 0,
      locked: false,
      cols: 4,
      rows: 4,
      players: [],
      currentPlayerIndex: 0
    };
```

- [ ] **Schritt 2: Setup-Variablen und -Funktionen nach `resetToStart()` einfügen**

Direkt nach der schließenden `}` von `resetToStart` einfügen:

```javascript
    let pendingPlayerCount = 0;
    let currentSetupIndex  = 0;

    function selectPlayerCount(count) {
      pendingPlayerCount = count;
      currentSetupIndex  = 0;
      state.players      = [];
      document.getElementById('setup-step1').classList.remove('active');
      document.getElementById('setup-step2').classList.add('active');
      document.getElementById('setup-player-title').textContent = 'Spieler 1 einrichten';
      const input = document.getElementById('player-name-input');
      input.value = '';
      input.classList.remove('error');
      input.focus();
    }

    function selectGender(gender) {
      const input = document.getElementById('player-name-input');
      const name  = input.value.trim();
      if (!name) {
        input.classList.add('error');
        input.focus();
        return;
      }
      input.classList.remove('error');

      const color = gender === 'boy' ? '#42a5f5' : '#e91e8c';
      const icon  = gender === 'boy' ? '👦' : '👧';
      state.players.push({ name, gender, icon, color, score: 0 });

      currentSetupIndex++;
      if (currentSetupIndex < pendingPlayerCount) {
        document.getElementById('setup-player-title').textContent =
          `Spieler ${currentSetupIndex + 1} einrichten`;
        input.value = '';
        input.focus();
      } else {
        showScreen('screen-difficulty');
      }
    }
```

- [ ] **Schritt 3: Im Browser testen**

Seite laden → "Los geht's!" klicken → 3 Spieler auswählen → Alle 3 Spieler konfigurieren. Erwartetes Ergebnis: Nach Spieler 3 erscheint `screen-difficulty`.

- [ ] **Schritt 4: Fehlerfall testen**

Auf "👦 Junge" klicken ohne Namen einzugeben. Erwartetes Ergebnis: Eingabefeld wird rot umrandet, Fokus bleibt im Feld.

- [ ] **Schritt 5: Commit**

```bash
git add memory.html
git commit -m "feat: add player setup logic with gender selection and validation"
```

---

### Task 4: JS — startGame, renderPlayerBadges, updatePlayerBadges

**Files:**
- Modify: `memory.html` — `startGame` anpassen, `renderPlayerBadges` und `updatePlayerBadges` hinzufügen

- [ ] **Schritt 1: `startGame` ersetzen**

Den kompletten `startGame`-Block ersetzen durch:

```javascript
    function startGame(pairs, cols, rows) {
      state.moves = 0;
      state.flippedCards = [];
      state.matchedPairs = 0;
      state.totalPairs = pairs;
      state.locked = false;
      state.cols = cols;
      state.rows = rows;
      state.currentPlayerIndex = 0;
      state.players.forEach(p => { p.score = 0; });

      document.getElementById('move-counter').textContent = 'Züge: 0';

      renderPlayerBadges();

      const chosen = shuffle([...EMOJIS]).slice(0, pairs);
      const cards  = shuffle([...chosen, ...chosen]);

      renderCards(cards, cols);
      showScreen('screen-game');
    }
```

- [ ] **Schritt 2: `renderPlayerBadges` und `updatePlayerBadges` nach `startGame` einfügen**

```javascript
    function renderPlayerBadges() {
      const container = document.getElementById('player-badges');
      container.innerHTML = '';
      state.players.forEach((player, i) => {
        const badge = document.createElement('div');
        badge.className = 'player-badge' + (i === state.currentPlayerIndex ? ' active' : '');
        badge.id = `badge-${i}`;
        if (i === state.currentPlayerIndex) badge.style.background = player.color;
        badge.textContent = `${player.icon} ${player.name} 0`;
        container.appendChild(badge);
      });
    }

    function updatePlayerBadges() {
      state.players.forEach((player, i) => {
        const badge = document.getElementById(`badge-${i}`);
        if (!badge) return;
        const isActive = i === state.currentPlayerIndex;
        badge.className = 'player-badge' + (isActive ? ' active' : '');
        badge.style.background = isActive ? player.color : '';
        badge.textContent = `${player.icon} ${player.name} ${player.score}`;
      });
    }
```

- [ ] **Schritt 3: Im Browser testen**

Spieler konfigurieren → Schwierigkeit wählen → Spielfeld öffnet sich. Erwartetes Ergebnis: Spieler-Badges erscheinen im Header, erster Spieler ist farbig hervorgehoben.

- [ ] **Schritt 4: Commit**

```bash
git add memory.html
git commit -m "feat: render player badges in game header with active highlight"
```

---

### Task 5: JS — checkMatch für Turnsystem anpassen

**Files:**
- Modify: `memory.html` — `checkMatch` ersetzen

- [ ] **Schritt 1: `checkMatch` komplett ersetzen**

```javascript
    function checkMatch() {
      const [a, b] = state.flippedCards;
      const player = state.players[state.currentPlayerIndex];

      if (a.dataset.emoji === b.dataset.emoji) {
        a.classList.add('matched');
        b.classList.add('matched');
        state.matchedPairs++;
        state.flippedCards = [];
        player.score++;
        updatePlayerBadges();

        if (state.matchedPairs === state.totalPairs) {
          setTimeout(showWin, 600);
        }
      } else {
        state.locked = true;
        setTimeout(() => {
          a.classList.remove('flipped');
          b.classList.remove('flipped');
          state.flippedCards = [];
          state.currentPlayerIndex =
            (state.currentPlayerIndex + 1) % state.players.length;
          state.locked = false;
          updatePlayerBadges();
        }, 1000);
      }
    }
```

- [ ] **Schritt 2: Im Browser testen — Treffer**

Spiel starten → zwei gleiche Karten finden. Erwartetes Ergebnis: Punktestand des aktiven Spielers steigt um 1, gleicher Spieler bleibt aktiv (Badge bleibt hervorgehoben).

- [ ] **Schritt 3: Im Browser testen — kein Treffer**

Zwei verschiedene Karten aufdecken. Erwartetes Ergebnis: Nach 1 Sekunde drehen die Karten zurück, das nächste Spieler-Badge leuchtet auf.

- [ ] **Schritt 4: Reihum-Logik mit 3 Spielern prüfen**

Mit 3 Spielern spielen: Spieler 1 → 2 → 3 → 1 → ... bestätigen.

- [ ] **Schritt 5: Commit**

```bash
git add memory.html
git commit -m "feat: implement turn-based multiplayer logic in checkMatch"
```

---

### Task 6: JS — showWin mit Rangliste

**Files:**
- Modify: `memory.html` — `showWin` komplett ersetzen

- [ ] **Schritt 1: `showWin` komplett ersetzen**

```javascript
    function showWin() {
      const sorted   = [...state.players].sort((a, b) => b.score - a.score);
      const maxScore = sorted[0].score;
      const winners  = sorted.filter(p => p.score === maxScore);

      const winnerDisplay = document.getElementById('winner-display');
      if (winners.length === 1) {
        winnerDisplay.innerHTML =
          `<p class="winner-name" style="color:${winners[0].color}">` +
          `✨ ${winners[0].icon} ${winners[0].name} hat gewonnen! ✨</p>`;
      } else {
        const names = winners.map(w => `${w.icon} ${w.name}`).join(' und ');
        winnerDisplay.innerHTML =
          `<p class="winner-name">🤝 Unentschieden!</p>` +
          `<p style="margin-bottom:12px">${names} — je ${maxScore} Paare</p>`;
      }

      const medals = ['🥇', '🥈', '🥉'];
      let rankIndex = 0;
      let prevScore = -1;
      const list = document.getElementById('ranking-list');
      list.innerHTML = '';
      sorted.forEach((player, i) => {
        if (player.score !== prevScore) { rankIndex = i; prevScore = player.score; }
        const medal = medals[rankIndex] !== undefined ? medals[rankIndex] : `${rankIndex + 1}.`;
        const li = document.createElement('li');
        li.textContent = `${medal} ${player.icon} ${player.name} — ${player.score} Paare`;
        list.appendChild(li);
      });

      showScreen('screen-win');
    }
```

- [ ] **Schritt 2: Im Browser testen — einzelner Gewinner**

Spiel zu Ende spielen (Leicht, 2 Spieler). Erwartetes Ergebnis: Gewinner-Name erscheint in seiner Farbe mit Pulsier-Animation, Rangliste zeigt 🥇🥈 korrekt.

- [ ] **Schritt 3: Unentschieden testen (manuell prüfen)**

In der Konsole `state.players[0].score = state.players[1].score = 4; state.matchedPairs = state.totalPairs; showWin();` eingeben. Erwartetes Ergebnis: "🤝 Unentschieden!" mit beiden Namen.

- [ ] **Schritt 4: Commit**

```bash
git add memory.html
git commit -m "feat: add win screen with ranking, winner animation, and tie handling"
```

---

### Task 7: JS — resetToStart aktualisieren

**Files:**
- Modify: `memory.html` — `resetToStart` ersetzen

- [ ] **Schritt 1: `resetToStart` komplett ersetzen**

```javascript
    function resetToStart() {
      state.moves = 0;
      state.flippedCards = [];
      state.matchedPairs = 0;
      state.locked = false;
      state.players = [];
      state.currentPlayerIndex = 0;
      document.getElementById('card-grid').innerHTML = '';
      document.getElementById('setup-step1').classList.add('active');
      document.getElementById('setup-step2').classList.remove('active');
      showScreen('screen-start');
    }
```

- [ ] **Schritt 2: Kompletten Flow testen**

Spiel spielen → Gewinn-Screen → "Nochmal spielen" klicken. Erwartetes Ergebnis: Startbildschirm erscheint, kein Fehler in der Konsole, setup-step1 ist wieder sichtbar.

- [ ] **Schritt 3: Zweites Spiel starten und prüfen**

Neues Spiel starten. Erwartetes Ergebnis: Spieler-Konfiguration beginnt von vorne, Badges zeigen 0 Punkte.

- [ ] **Schritt 4: Commit**

```bash
git add memory.html
git commit -m "feat: reset all player state and setup screen on resetToStart"
```

---

### Task 8: Finaler Push zu GitHub

**Files:**
- Kein neuer Code

- [ ] **Schritt 1: Status und Log prüfen**

```bash
cd "c:/Workspace/Software/Games/wurmspiele"
git log --oneline -10
git status
```

Erwartetes Ergebnis: Kein uncommitted change. Alle 7 neuen Commits seit letztem Push sichtbar.

- [ ] **Schritt 2: Pushen**

```bash
git push origin master
```

- [ ] **Schritt 3: Bestätigen**

```bash
gh browse
```

Erwartetes Ergebnis: `memory.html` auf GitHub mit den neuesten Commits.

---

## Spec-Abdeckung

| Anforderung | Task |
|-------------|------|
| screen-start → "Los geht's!" Button | Task 2 |
| screen-setup: Spieleranzahl 2–6 | Task 2+3 |
| screen-setup: Name + Geschlecht pro Spieler | Task 2+3 |
| Validierung leerer Name | Task 3 |
| Spielerfarbe: Junge blau, Mädchen pink | Task 3 |
| screen-difficulty ausgelagert | Task 2 |
| state.players + currentPlayerIndex | Task 3 |
| Spieler-Badges im Header | Task 4 |
| Aktiver Spieler hervorgehoben | Task 4 |
| Treffer → Punkt + gleicher Spieler | Task 5 |
| Kein Treffer → nächster Spieler | Task 5 |
| Gewinn-Screen: Gewinner-Name animiert | Task 6 |
| Gewinn-Screen: Rangliste mit Medaillen | Task 6 |
| Unentschieden-Behandlung | Task 6 |
| resetToStart setzt alles zurück | Task 7 |
