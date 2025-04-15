p_followup_questions = """Prämisse: Es wird angenommen, dass alle Teilnehmenden über umfangreiche Erfahrung in der Betreuung und Begleitung von Menschen mit Demenz verfügen. Das Berufsfeld ist: {business_segment}, mit einem besonderen Fokus auf demenzspezifische Aspekte.

Basierend auf dem bereitgestellten Kontext und dem letzten Frage-Antwort-Paar, formuliere bis zu drei zusätzliche Fragen, die bisher nicht berücksichtigte, aber relevante Themen im Umgang mit Demenzpatient*innen aufgreifen - insbesondere solche, die praktische, ethische oder emotionale Herausforderungen betreffen. Überprüfe auch die Liste der kommenden Fragen auf ihre Relevanz im Kontext der Demenzversorgung und entferne bis zu 30 % der Fragen, die für diesen Kontext weniger bedeutsam erscheinen. Achte darauf, dass die neuen Fragen keine Wiederholungen oder Varianten bereits behandelter Fragen sind.

Formatiere das Ergebnis als JSON-Objekt gemäß der angegebenen Struktur.

Kontext: {history}

Letzte Frage und Antwort:
Frage: {question}
Antwort: {message}
Geplante notwendige Fragen: {mandatory_upcoming_questions}
Geplante optionale Fragen: {optional_upcoming_questions}
Übersprungene Fragen: {skipped_questions}

Regeln:
- Generiere bis zu 3 weitere Fragen.
- Vermeide Duplikation oder zu große Ähnlichkeit zu den geplanten, optionalen und übersprungenen Fragen.
- Entferne bis zu 30% der weniger relevanten optionalen Fragen basierend auf dem aktuellen Kontext.

Beispiel für eine JSON-Rückgabe
```
{ 
"concepts":  ["Konzept 1", "Konzept 2"], 
"additional_questions": [ "Frage 1?", "Frage 2?" ], 
"removed_optional_questions": [ "Optionale Frage 3?" ], 
"notes": "Zwei zusätzliche Fragen wurden generiert, um wichtige fehlende Informationen zu erfassen. Eine weniger relevante Frage wurde entfernt." 
}
```
"""

# WIKI

p_wiki = """
Gegeben ist der folgende Text einer Konversation zwischen zwei Fachkräften, die in unterschiedlichen oder ähnlichen Rollen im Bereich der Demenzversorgung tätig sind. In diesem speziellen Fall geht es um: {business_segment}.
Die Unterhaltung dient dem professionellen Austausch und verfolgt das Ziel, Wissen zu teilen, Erfahrungen zu reflektieren und Prozesse rund um die Betreuung von Menschen mit Demenz nachvollziehbar zu dokumentieren:

{conversation}

Deine Aufgabe ist es, aus der Konversation eine Wiki-Seite im Markdown-Format zu erstellen, die die wesentlichen Informationen, Erfahrungen und Vorgehensweisen klar und verständlich zusammenfasst. Ziel ist es, eine praxisnahe Wissensgrundlage zu schaffen, die auch für Personen ohne tiefgehende Vorerfahrung im Demenzbereich nachvollziehbar ist. Neben fachlichen Informationen soll auch zwischen den Zeilen lesbares Erfahrungswissen (implizites Wissen) dokumentiert werden.

Die Wiki soll folgende Elemente enthalten:

    TLDR: Kurze Zusammenfassung der wichtigsten Erkenntnisse und demenzbezogenen Aspekte.

    Überblick über die zentralen Themen und Anliegen der Gesprächspartner*innen.

    Schlüsselkonzepte rund um Demenz, Kommunikation, Pflege oder Therapieansätze.

    Explizites Wissen wie Definitionen, eingesetzte Methoden, Hilfsmittel oder Abläufe.

    Implizites Wissen wie Erfahrungswerte, typische Herausforderungen oder bewährte Vorgehensweisen im Umgang mit Demenz.

    Prozesse und Verfahren als Schritt-für-Schritt-Beschreibungen für relevante Abläufe.

    Visualisierungen (optional), z. B. einfache Ablaufdiagramme zur Darstellung von Pflegeschritten, Kommunikationsmethoden oder Interventionsplänen.

    Empfohlene Ressourcen und weiterführende Fragen, die sich aus dem Gespräch ergeben.

    Feedback und Meinungen der Beteiligten, insbesondere persönliche Einschätzungen aus der Praxis.

    Zusammenfassung der Kernpunkte als schnelle Orientierungshilfe.

Bitte strukturiere die Wiki wie folgt:
```
# Konversationsthema: {{Thema der Konversation}}

## TLDR
- Kurze Zusammenfassung der wichtigsten Erkenntnisse im Kontext der Demenzversorgung.

## Überblick
- Hauptthemen und Ziele der Unterhaltung.

## Schlüsselkonzepte
- Beschreibung zentraler Begriffe und Ideen im Umgang mit Menschen mit Demenz.

## Explizites Wissen
- Klare Informationen über Methoden, Werkzeuge und konkrete Vorgehensweisen.

## Implizites Wissen
- Reflexion von Praxiserfahrung, bewährten Tipps und stillschweigendem Wissen.

## Prozesse und Verfahren
- Schritt-für-Schritt-Anleitungen relevanter Abläufe.

## Visualisierungen (optional)
- Diagramme oder Flusscharts zur Veranschaulichung der Abläufe.

## Empfohlene Ressourcen und weiterführende Fragen
- Links, Buchtipps oder Impulse zur Vertiefung der Themen.

## Feedback und Meinungen
- Persönliche Einschätzungen und Meinungen der Beteiligten zum Thema.

## Zusammenfassung
- Kompakte Wiederholung der wichtigsten Punkte zur schnellen Orientierung.
```
"""
