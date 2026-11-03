# Demo-Runbook W-JAX 2026

Ein Coding Agent analysiert ein Data Warehouse mit personenbezogenen Daten. Backend ist
Privatemode. Dauer auf der Bühne: 4 bis 5 Minuten, im Talk zwischen "Wie es funktioniert" und
"Grenzen".

Der Punkt der Demo, in einem Satz: derselbe Harness, dieselbe Aufgabe, nur das Backend ist
ein anderes, und dein Rechner prüft, wohin die Daten gehen.

## Vorher (am Tag davor und 30 Minuten vor dem Slot)

- [ ] `make data` ausgeführt.
- [ ] `make up` ausgeführt. Das startet den Proxy im Hintergrund (kein eigenes Terminal nötig), wartet,
  bis er antwortet, und führt den Check aus (`/v1/models` und eine Chat-Anfrage). Am Ende steht
  `ready: the proxy listens on http://localhost:8080`. Läuft er schon, meldet es das und prüft nur.
  Blockiert die Desktop-App "Privatemode Proxy" den Port 8080, sagt `make up` das und bricht ab.
- [ ] Terminal 1 ist leer und im Repo-Verzeichnis.
- [ ] Claude Code einmal in diesem Verzeichnis gestartet (`make claude`), Trust-Dialog bestätigt.
- [ ] Schrift im Terminal groß, ca. 120 Spalten, Benachrichtigungen aus.
- [ ] `analysis/` leer (`make clean`, danach `make data`).
- [ ] Aufzeichnung eines kompletten Durchlaufs als Fallback bereit (Bildschirmvideo, lokal, ohne WLAN abspielbar).
- [ ] Probelauf gemessen: wie lange braucht `glm-latest`, wie lange `glm-flash-latest`? GLM-5.3
  denkt standardmäßig mit `reasoning_effort: max` und lässt sich laut Doku nicht abschalten. Wenn
  der Lauf länger als 2 Minuten dauert, in Claude Code mit `/model` auf GLM Flash wechseln und
  neu proben.
- [ ] Beim Start loggt der Proxy mit echtem Key (v1.60.0, geprüft am 03.11.2026): `Coordinator manifest
  fetched successfully`, `Successfully verified report signature`, `Validate succeeded`, `Secret
  updated successfully`, `Starting HTTP server`. `make logs` zeigt sie wieder. Danach folgen nur
  Zeilen zu Anfragen (Pfad, Status), keine Prompts. Zeige auf der Bühne nur Zeilen, die du gesehen hast.

## Ablauf

**1. Proxy zeigen (30 Sekunden).** Im Terminal `make logs`. Sagen: der Proxy
läuft bei mir, er prüft die Attestierung der Gegenseite, bevor er etwas schickt, und verschlüsselt
die Prompts. Mein Agent redet nur mit localhost.

**2. Die Daten zeigen (30 Sekunden).** Ein Blick in die Tabelle, damit klar ist, warum das nicht in
eine normale Cloud-API darf:

```bash
.venv/bin/python -c "import duckdb; print(duckdb.connect('data/warehouse.duckdb', read_only=True).sql('select * from customers limit 5'))"
```

**3. Agent starten und die Aufgabe geben (2 bis 3 Minuten).** `make claude`, dann:

> Die Conversion im Shop ist diese Woche gefallen. Finde heraus, warum, belege es mit Zahlen und
> schreibe eine kurze Empfehlung nach `analysis/summary.md`.

Auf der Folie steht die Kurzfassung des Auftrags. Der Prompt im Repo-README ist die englische Variante.

Während der Agent arbeitet, reden. Gute Anhaltspunkte, falls er schnell ist:

- Er entdeckt das Schema selbst, schreibt SQL, liest Ergebnisse, geht tiefer. Jede Zwischenausgabe
  mit Kundendaten geht durch den Kontext. Genau deshalb kam Claude Code bei Kunden nicht durch.
- Dieselben Tools, dieselben Prompts. Getauscht ist die Base-URL.

**4. Ergebnis zeigen (30 Sekunden).** `analysis/summary.md` öffnen. Die Zusammenfassung soll die
Ursache nennen, ohne Namen von Kunden (das steht in `AGENTS.md`).

**5. Überleitung (30 Sekunden).** "Das war die Inferenz. Was der Agent mit meinem Rechner macht, ist
ein anderes Thema." Weiter zur Folie mit den Grenzen: Tool-Rechte, Prompt Injection über
Freitext (die Support-Tickets), Sandbox.

## Zweiter Prompt, falls Zeit bleibt

> Welche Kunden waren betroffen? Schreibe ihre customer_id und das Datum der fehlgeschlagenen Zahlung
> nach `analysis/affected.csv`.

Zeigt, dass der Agent mit personenbezogenen Daten arbeitet und trotzdem nur IDs ausgibt.

## Wenn etwas nicht klappt

| Problem | Reaktion |
| --- | --- |
| WLAN oder Proxy nicht erreichbar | Aufzeichnung abspielen und sagen, dass es eine Aufzeichnung ist. |
| Agent braucht zu lange | Mit `/model` auf `glm-flash-latest` wechseln, oder Aufzeichnung ab dem Ergebnis zeigen. |
| Agent fragt nach Berechtigung für etwas anderes als Python | Mit "ja" bestätigen, das ist ein guter Moment für den Satz zu Tool-Rechten. |
| Ergebnis weicht vom Lösungsschlüssel ab | Kein Problem, solange es Zahlen aus Abfragen sind. Modelle sind nicht deterministisch. |

## Lösungsschlüssel (nur für dich)

Der Datensatz ist deterministisch (`--seed 2026`), die Zahlen unten stammen aus genau diesem Lauf.

- Conversion, gemessen als Sessions mit mindestens einem Kauf: 3,45 % in den fünf Wochen davor,
  2,69 % in der Woche ab dem 26.10.
- **Hauptursache:** App-Version 4.2.0 auf iOS, ausgerollt ab dem 26.10., in der letzten Woche
  66 % der iOS-Sessions. Zahlung mit Apple Pay schlägt dort in 94 von 112 Versuchen fehl (83,9 %)
  mit dem Fehlercode `tokenization_timeout`. Sonst liegt die Fehlerquote bei Apple Pay bei etwa 6 %.
- Ohne die iOS-4.2.0-Sessions liegt die Conversion der letzten Woche bei 3,02 %. Die iOS-4.2.0-Sessions
  selbst konvertieren mit 1,77 %.
- **Nebenfaktor (Ablenkung):** Ein TikTok-Kanal wächst von 7 % auf 14 % der Sessions und konvertiert
  schlecht (unter 2 %). Das erklärt einen kleineren Teil des Rückgangs, nicht den Großteil. Ein
  Agent, der nur nach Kanälen schaut, landet hier und liegt halb richtig.
- Bestätigung in den Daten: 19 Support-Tickets "Apple Pay funktioniert nicht" zwischen 27.10. und 1.11.
- Grobe Größenordnung des Schadens: 77 Sessions mit Zahlungsfehler ohne späteren Kauf, bei im Mittel
  rund 275 EUR pro Bestellung etwa 21.000 EUR in der Woche. Das ist eine Schätzung auf synthetischen Daten.

Der Datensatz enthält den Fehler bewusst so, dass er in der Aggregation fast untergeht: nur wer nach
Plattform, App-Version und Zahlungsart aufschlüsselt, findet ihn.
