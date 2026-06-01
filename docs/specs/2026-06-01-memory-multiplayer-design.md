# Memory-Spiel Multiplayer — Design-Dokument

**Datum:** 2026-06-01
**Repo:** carloco1/wurmspiele
**Datei:** `memory.html` (Erweiterung des bestehenden Spiels)
**Basis:** `docs/superpowers/specs/2026-06-01-memory-game-design.md`

---

## Übersicht

Erweiterung des bestehenden Memory-Spiels um Mehrspielermodus (2–6 Spieler) mit Geschlechtsauswahl (Mädchen/Junge) pro Spieler. Das Spiel bleibt eine einzige HTML-Datei ohne externe Abhängigkeiten.

---

## Neuer Screen-Flow

```
screen-start → screen-setup → screen-difficulty → screen-game → screen-win
```

**Änderungen gegenüber v1:**
- `screen-start`: Die 3 Schwierigkeits-Buttons werden entfernt. Stattdessen ein einzelner Button "🎮 Los geht's!" der `screen-setup` anzeigt. Titel und Beschreibungstext bleiben.
- `screen-setup`: Neu — Spieleranzahl + Spieler-Konfiguration
- `screen-difficulty`: Neu (ausgelagert aus `screen-start`) — Leicht/Mittel/Schwer Auswahl
- `screen-game`: Erweiterter Header mit Spieler-Badges und Turnanzeige
- `screen-win`: Erweiterter Gewinn-Screen mit Rangliste

---

## screen-setup (neu)

### Schritt 1 — Spieleranzahl

- Titel: "Wie viele Spieler?"
- 5 Buttons: 2 / 3 / 4 / 5 / 6
- Nach Klick: Schritt 2 erscheint (Schritt 1 wird ausgeblendet)

### Schritt 2 — Spieler einrichten (einer nach dem anderen)

Für jeden Spieler (i = 1 bis N):
- Überschrift: "Spieler [i] einrichten"
- Namens-Eingabefeld (Pflicht, max. 12 Zeichen), Placeholder: "Name eingeben"
- Zwei Buttons: `👦 Junge` (blau) und `👧 Mädchen` (pink)
- Klick auf Geschlecht → Spieler wird gespeichert, nächster Spieler erscheint
- Wenn alle Spieler eingerichtet: Weiter zu `screen-difficulty`

**Validierung:** Name darf nicht leer sein. Bei leerem Feld wird kein Spieler gespeichert und der Fokus bleibt im Eingabefeld.

---

## screen-difficulty (neu)

Ausgelagerter Screen mit den Schwierigkeits-Buttons (identisch zu bisherigem `screen-start`):
- 🌱 Leicht — 8 Paare · 4×4
- 🌿 Mittel — 12 Paare · 4×6
- 🌳 Schwer — 18 Paare · 6×6

Klick startet das Spiel mit den konfigurierten Spielern.

---

## Spieler-Datenmodell

```javascript
// Spieler-Objekt
{ name: "Max", gender: "boy", color: "#42a5f5", score: 0 }
// gender: "boy" → color: "#42a5f5" (blau)
// gender: "girl" → color: "#e91e8c" (pink)

// Erweiterung des state-Objekts
state = {
  ...// bisherige Felder bleiben
  players: [],          // Array von Spieler-Objekten
  currentPlayerIndex: 0 // Index des aktiven Spielers
}
```

---

## screen-game Header (erweitert)

```
┌──────────────────────────────────────────────────────────┐
│  [Badge1] [Badge2] ... [BadgeN]  │  Züge: 0  │  ↩ Neu  │
└──────────────────────────────────────────────────────────┘
```

**Spieler-Badge:**
- Icon (👦/👧) + Name + Punktestand: `👦 Max 3`
- Hintergrundfarbe des aktiven Spielers (blau/pink), andere ausgegraut (`#ccc`)
- Leicht vergrößert (scale 1.05) wenn aktiv

**Turnsystem:**
1. Aktiver Spieler deckt 2 Karten auf
2. **Treffer:** `score++`, Badge aktualisiert, gleicher Spieler bleibt aktiv
3. **Kein Treffer:** Karten drehen zurück nach 1 Sek., `currentPlayerIndex = (currentPlayerIndex + 1) % players.length`

---

## screen-win (erweitert)

### Gewinner ermitteln

```javascript
const maxScore = Math.max(...players.map(p => p.score));
const winners = players.filter(p => p.score === maxScore);
```

### Anzeige bei einem Gewinner

```
        🎉🏆🎉
  ✨ [Name] hat gewonnen! ✨   ← in Spielerfarbe, Pulsier-Animation
  
  🥇  👦 Max    — 6 Paare
  🥈  👧 Lisa   — 4 Paare
  🥉  👦 Tim    — 2 Paare

  [ 🔄 Nochmal spielen ]
```

### Anzeige bei Unentschieden

```
  🤝 Unentschieden!
  👦 Max und 👧 Lisa — je 5 Paare
  
  [ Rangliste... ]
```

**Rangliste:** Spieler sortiert nach Score absteigend. Gleicher Score → gleiche Medaille. Medaillen: 🥇🥈🥉, ab Platz 4: Platznummer.

### Button

"🔄 Nochmal spielen" → `resetToStart()` — setzt alle Spieler-Daten und state zurück, zeigt `screen-start`

---

## CSS-Ergänzungen

- `.player-badge`: Badge-Stil, standardmäßig ausgegraut
- `.player-badge.active`: Spielerfarbe als Hintergrund, leicht skaliert
- `.winner-name`: Große Schrift, Pulsier-Keyframe-Animation (`@keyframes pulse`)
- `.ranking-list`: Flex-Column für die Rangliste

---

## Nicht im Scope

- Spieler können ihren Namen während des Spiels ändern
- Zeitlimit pro Zug
- Sound-Effekte
- Online-Multiplayer
- Highscore-Speicherung zwischen Sitzungen
