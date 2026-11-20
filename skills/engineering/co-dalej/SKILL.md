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
| spec | `.scratch/<feature>/spec.md`, zgłoszenie z etykietą spec |
| bilety | `.scratch/<feature>/issues/*`, tracker opisany w `docs/agents/issue-tracker.md` |
| praca w toku | `git status`, `git diff --stat`, gałąź względem main |
| konfiguracja | `docs/agents/` (brak = setup jeszcze nie był) |

Nie zgaduj — otwórz katalogi i sprawdź, co realnie leży. Brak artefaktu to informacja, nie błąd.

## 2. Wybierz jeden krok

Od góry, pierwsze trafienie wygrywa:

0. **Brak `docs/agents/`** → `/setup-matt-pocock-skills`. Reszta skilli czyta z tych plików tracker
   i ścieżki; bez nich każdy kolejny krok zgaduje.
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


## Budżet kontekstu

Sesja ma skończyć się **przed** wyczerpaniem okna, nie po. Cel: 110–130k tokenów na sesję, twardy
sufit 150–180k. Sprawdzaj zużycie na granicy każdego kroku, nie w jego środku:

| Zużycie | % okna 200k | Decyzja |
|---|---|---|
| do ~80k | < 40% | następny krok bez ograniczeń |
| 80–120k | 40–60% | dokończ bieżący krok i **zamknij na granicy fazy** |
| 120–150k | 60–75% | nie zaczynaj nowego kroku: zapisz handoff i zakończ |
| > 150k | > 75% | tylko handoff w pięciu liniach, potem stop |

Jeśli harness nie pokazuje zużycia tokenów, użyj proxy i oceniaj ostrożnie: **liczba tur** (ponad 25
to koniec fazy), liczba wczytanych dużych plików (ponad 15), rozmiar diffu, liczba wywołań narzędzi
w jednej turze. Lepiej zamknąć sesję o 10% za wcześnie niż urwać ją w połowie kroku.

Na granicy fazy wybierz jedno: `/compact` (streszczenie, ten sam task — traci szczegóły) albo
**New Task + handoff** (czysty kontekst — zachowuje to, co zapiszesz). Handoff to pięć linii: co
zrobione, co zostało, gdzie leży plan, jaki jest następny krok, czego nie ruszać. Nie compactuj
w środku kroku i nie przenoś sesji „na chwilę” — przeniesienie kosztuje więcej niż dokończenie.

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
