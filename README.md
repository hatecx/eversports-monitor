# Pilates-Kurswächter – Studio Balance by Elif

Ein getrenntes Projekt zur öffentlichen Eversports-Abfrage. Liest jede Woche bis 21 Tage ab morgen, prüft die tatsächlichen Kursdetails vor einer Push-Nachricht und vermeidet Duplikate per `data/notified.json`.

## Noch nicht produktiv!

Vor Veröffentlichung muss die echte GitHub-Actions-Umgebung mit `workflow_dispatch` (`dry_run: true`) getestet werden. Nur wenn alle Wochen sichtbar geladen werden, Details `N remaining` zeigen und `Book now` erreichbar ist, ist ein Push erlaubt. Anschließend ntfy mit `dry_run: false` Ende-zu-Ende prüfen. Die öffentliche ntfy-Instanz besitzt keine privaten Themen: Wer den Namen kennt, kann Nachrichten lesen oder veröffentlichen.

## Voraussetzungen

- Eigenes GitHub-Repository (nicht Finora / Unser Zuhause), Actions aktiviert.
- GitHub Actions `GITHUB_TOKEN` darf Repository-Inhalte schreiben, damit der Benachrichtigungsstatus über Läufe hinweg gespeichert wird.
- Bereits abonniertes ntfy-Thema `pilates-elif-k7m29q84x`.
- Keine Eversports-Anmeldung und keine kostenpflichtige API.

## Testbefehle

```sh
python -m unittest test_monitor.py
python -m playwright install chromium
DRY_RUN=true python monitor.py
```

Workflow: zwei UTC-Zeiten (17 und 18 Uhr) plus Prüfung des deutschen UTC-Offsets; daher jeweils nur **ein** Lauf pro Tag entsprechend Europe/Berlin. GitHub Actions garantiert allerdings keine minutengenaue Ausführung.
