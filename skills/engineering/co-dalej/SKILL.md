---
name: co-dalej
description: Powiedz, który krok workflow wykonać teraz, na podstawie stanu repo.
---

# Co dalej

Użytkownik nie zna jeszcze kolejności skilli i pyta „co teraz?”. Twoim zadaniem jest ustalić,
**gdzie w workflow jest**, i podać **jeden** następny krok — nie mapę.

## 1. Ustal stan repo (czytaj, nie pytaj)

| Artefakt | Gdzie szukać |
|---|---|
| ledger wywiadu | `wiki/processes/grill/*.md`, `docs/agents/grill/*.md`, `.scratch/grill/*.md` |
| słownik pojęć | `GLOSSARY.md`, `docs/agents/domain.md` |
| decyzje (ADR) | `wiki/decisions/`, `docs/adr/`, `docs/agents/decisions/` |
| spec | `docs/agents/specs/*`, zgłoszenie z etykietą spec |
| bilety | `docs/agents/tickets/*`, `.scratch/<feature>/issues/*`, tracker |
| praca w toku | `git status`, `git diff --stat`, gałąź względem main |
| zgłoszenia | tracker wskazany w `docs/agents/domain.md` |

Nie zgaduj — otwórz katalogi i sprawdź, co realnie leży. Brak artefaktu to informacja, nie błąd.

## 2. Wybierz jeden krok

Od góry, pierwsze trafienie wygrywa:

1. **Jest pomysł, nie ma ledgera** → `/grill-with-docs`.
2. **Jest ledger, brak słownika** → `/grill-with-docs` (dokończ nazwy). Nie `/to-spec` — spec bez
   nazw to zgadywanie.
3. **Słownik jest, brak spec, robota wielosesyjna** → `/to-spec`.
4. **Jest spec, brak biletów** → `/to-tickets`.
5. **Są bilety, brak kodu** → `/implement` (bilet po bilecie, nowa sesja między) albo
   `/implement-spec` (całość jednym przebiegiem).
6. **Jest kod, brak review** → `/code-review`.
7. **Review zrobiony, jest commit/PR** → `/retro`, jeśli fala była duża; inaczej koniec zadania.
8. **Pytanie „czy codebase to już ma?”** → `/triage` na zgłoszeniach, potem `/implement`.
9. **„Nie umiem tego rozbić na kawałki”** → `/wayfinder`.
10. **Review drugi raz łapie to samo** → `/retro`, i wniosek zamień w regułę, nie w kolejną poprawkę.
11. **Zmiana jest drobna i jednostrzałowa** → `/implement` od razu; spec i bilety to biurokracja.

## 3. Odpowiedz w tym formacie

```
**Stan:** <co jest, czego brakuje — po jednym artefakcie na linię>
**Rekomenduję:** `/<skill>` — <co da i ile zajmie>
**Albo:** `/<skill>` (kiedy), `/<skill>` (kiedy)
```

Trzy opcje to maksimum. Skończ pytaniem **„idziemy w to?”** i czekaj na odpowiedź.

## Czego nie robić

- Nie wypisuj całej mapy skilli — od tego jest `/ask-matt`.
- Nie zaczynaj kroku bez potwierdzenia, nawet gdy rekomendacja jest oczywista.
- Nie proponuj kroku, którego artefakt już istnieje (np. `/to-spec`, gdy spec leży w repo).
- Nie mieszaj „poza zakresem” z „do zrobienia później”: pierwsze idzie do ledgera, drugie do
  zgłoszeń.

## Wersja Kilo

Skille wywołujesz jak komendy (`/grilling`, `/to-spec`). Granice faz: **New Task** = czysty
kontekst, `/compact` = streszczenie w tym samym tasku, komenda z `subtask: true` = subagent.
Nie compactuj w środku fazy — tylko na granicy (wywiad → spec → bilety → implementacja).
