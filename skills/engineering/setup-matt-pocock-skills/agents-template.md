---
status: ACTIVE
last_updated: <RRRR-MM-DD>
last_verified: <RRRR-MM-DD>
verified_against_snapshot: <nazwa snapshotu lub USER-<temat>-<data>>
related_objects: []
---
# Zasady projektu

> Szablon. Wypełnij `<...>` i **usuń sekcje, które nie dotyczą tego repo** — martwa sekcja
> czyta się jak wymaganie i prędzej czy później ktoś ją wypełni bzdurą. Krótszy plik, który
> wszystko pokrywa, jest lepszy od kompletnego, którego nikt nie czyta.

## 1. Zakres i autorytet

- Repo: `<ścieżka>`. Ograniczaj wyszukiwania i zapisy do tego katalogu, nie do `C:/`.
- Jedyne aktywne źródła: `<pliki/katalogi>`. Zastane pliki są aktualne, dopóki nie udowodnisz
  inaczej — brak zgodności z archiwum nie jest błędem.
- Nie czytaj starego repo ani archiwum bez wykazanej potrzeby.
- Pamięć, podpowiedzi edytora, zastane symbole i stare notatki **nie są dowodem** obecnego
  działania. Sprawdź plik albo stan narzędzia.
- `<ograniczenia środowiska: brak admina, brak sieci, brak remote, polityka firmowa>`.

## 2. Autonomia agenta

- Upoważnienie obejmuje: analizę, dokumentację, testy na kopiach, bezpieczne poprawki techniczne
  i commity w zakresie tego pliku. Nie czekaj na zgodę przy każdym kroku w tym zakresie.
- Przed większą zmianą zapisz plan: cel, źródła, zależności, ryzyko, kolejność, testy, rollback.
- Nie kończ na pierwszym zadaniu. Pytania biznesowe, których nie rozstrzygniesz sam, zbieraj
  do raportu zamiast przerywać pracę.
- Blokery: `TASK_BLOCKER` blokuje obiekt, `DOMAIN_BLOCKER` obszar, `GLOBAL_BLOCKER` całość.
  Zapisuj dowody, próby i zadania zależne. Zatrzymaj globalnie tylko realnie niebezpieczną
  albo nieupoważnioną pracę.
- Maksymalnie trzy uzasadnione próby; każda długa operacja z timeoutem. Po timeoucie sprawdź
  stan poprzedniego procesu. Nie zabijaj procesów ani nie usuwaj blokad użytkownika.
- Konfiguracja narzędzi (setup skilli, `docs/agents/`) **nie jest etapem roboczym** i nie zużywa
  numeru etapu, jeśli repo je numeruje. Idzie do `CHANGELOG.md` jako wpis konfiguracyjny.

## 3. Bezpieczna edycja tekstu

- Jeden plik ma jednego właściciela zapisu w danym czasie. Przed delegacją przypisz konkretne
  pliki; pozostali agenci przekazują propozycje właścicielowi. Subagenci nie nadpisują cudzych
  eksportów.
- Po pierwszym błędzie „nie znalazłem oczekiwanych linii” **nie ponawiaj tego samego patcha**.
  Odczytaj aktualny plik i otoczenie, sprawdź `git diff` i czy poprawka już nie jest wykonana.
- Przed nową edycją potwierdź rolę pliku (źródło, propozycja, fixture, narzędzie, dokumentacja)
  i sprawdź, czy od odczytu nie zmienił go ktoś inny.
- Po zapisie **odczytaj wynik** i sprawdź diff. Brak błędu narzędzia nie zastępuje readbacku.
- Nie usuwaj kontroli dopasowania, nie rób ślepego globalnego replace, nie nadpisuj całego
  modułu jako obejścia błędu patcha.
- Skrypt zamieniający tekst sprawdza oczekiwaną liczbę wystąpień **przed** zapisem i przerywa
  przy rozbieżności. Zachowuje kodowanie i format pliku.

## 4. Granice zmian

- Bez osobnej decyzji nie zmieniaj: historycznych statusów, identyfikatorów, danych finansowych,
  podpisanych publikacji ani logów; nie usuwaj walidacji i kontroli.
- **Kandydat do usunięcia nie jest zgodą na usunięcie.** Klasyfikuj: `ACTIVE`, `UNCERTAIN`,
  `DEPRECATION_CANDIDATE`, `APPROVED_FOR_REMOVAL`. Brak wyniku wyszukiwania nie dowodzi martwości
  — sprawdź wywołania dynamiczne, konfigurację, zdarzenia i inne pliki.
- Migracje nazw rób osobno, bez globalnego usuwania; zachowaj wersje schematów wymiany.
- Publikacja do innych osób, upload, wysyłka i deploy wymagają jawnego potwierdzenia operacji.

## 5. Skoroszyty i Excel (usuń, jeśli projekt ich nie dotyczy)

- Ekstrakcja najpierw **pasywna**. Nie odświeżaj, nie aktualizuj linków, nie uruchamiaj
  nieznanych makr.
- Runtime wyłącznie na izolowanych kopiach: własna niewidoczna instancja (`DispatchEx`), makra
  i zdarzenia wyłączone **przed** otwarciem, `UpdateLinks=0`.
- Żadnego zapisu aktywnych plików przez `openpyxl`/`pandas` ani LibreOffice — gubią części pakietu.
- Przed pierwszą modyfikacją binarium: test no-op open/save i sprawdzenie, że istotne części
  pakietu przeżywają zapis.
- Formularz bez pliku `.frx` nie jest pełnym źródłem. **Git nie odtwarza aplikacji** — binaria
  zabezpieczaj baseline'em i checkpointem.
- Nie obchodź ochrony VBA/IRM i nie odtwarzaj skoroszytu, żeby zrobić drobną zmianę.
- Rozróżniaj dowód: inspekcja pliku ≠ otwarcie ≠ kompilacja ≠ uruchomiony scenariusz.

## 6. Wiki i wiedza

- Zaczynaj od `wiki/index.md`. Jeden artefakt ma jedno miejsce; reszta linkuje, nie kopiuje.
- Utrzymywane strony mają `status`, `last_updated`, `last_verified`, `verified_against_snapshot`,
  `related_objects`. `last_verified` zmieniaj **tylko po realnym ponownym sprawdzeniu** — nie po
  edycji literówki i nie dlatego, że powstał commit.
- Fakty oznaczaj `USER_CONFIRMED` / `OBSERVED` / `INFERRED` / `PROPOSED`. Nieznane i przestarzałe
  opisuj jawnie.
- Decyzje: `wiki/decisions/NNNN-<slug>.md`. Jeśli rejestr jest jednym plikiem (`decisions.md`),
  pełni rolę **indeksu** — bez zmiany nazwy i bez przenoszenia.
- Dwie kolejki o różnych zakresach: `.scratch/` to zadania prowadzone przez engineering skills
  (spec, tickety, wywiady), `wiki/` to wiedza projektu. Ten sam bilet nie istnieje w obu.
- Bez wiki: ADR-y w `docs/adr/`, ledger wywiadu w `docs/agents/grill/`.

## 7. Skille Matta w Kilo

- Setup uruchamia się **raz na repo**: `docs/agents/issue-tracker.md`, `triage-labels.md`,
  `domain.md`. Reszta skilli czyta z nich tracker i ścieżki — bez nich każdy krok zgaduje.
- Kolejność: `/grill-with-docs` → `/to-spec` → `/to-tickets` → `/implement` (bilet po bilecie)
  → `/code-review` → `/retro` po dużej fali.
- Gdy nie wiesz, co dalej: `/co-dalej` — czyta stan repo i podaje **jeden** krok, nie mapę.
- Nie uruchamiaj skillu, którego artefakt już istnieje (np. `/to-spec`, gdy spec leży w repo).
- `New Task` = czysty kontekst; `/compact` = streszczenie w tym samym tasku. Nie compactuj
  w środku fazy, tylko na granicy: wywiad → spec → bilety → implementacja.
- Spec zostaje w trackerze, wiedza w wiki. Skill nie jest źródłem prawdy o projekcie — jest nim
  ten plik i `docs/agents/*`.

## 8. Git i wersjonowanie

- Po każdym zaakceptowanym kawałku pracy: `git status` i commit z opisem **co i dlaczego**.
  Nie zostawiaj brudnego drzewa na koniec rundy.
- Stageuj jawnie. Zakaz `git add -A`, `reset --hard`, `clean`, przepisywania historii i cofania
  cudzych zmian.
- Nie pushuj bez zgody. Nie force-pushuj.
- Nie commituj: sekretów, surowych danych biznesowych, binariów (`.xlsx`, `.xlam`, `.frx`)
  i dużych artefaktów.
- Podział odpowiedzialności: `CHANGELOG.md` = co się zmieniło i dlaczego, `wiki/decisions/` =
  dlaczego tak zdecydowano, tracker = co jeszcze zostało, commit = niepodzielna całość.

## 9. Etapy (opcjonalne — usuń, jeśli repo ich nie ma)

- Etap to **widok**, nie licznik zadań. Jeśli repo prowadzi etapy, nazywaj je nazwą i datą;
  numer jest dopuszczalny tylko jako trwały identyfikator historyczny.
- Nie renumeruj zapisanych etapów. Nowa reguła obowiązuje od teraz, stara historia zostaje.
- Etap zamyka się `CHANGELOG.md` (zmiany, decyzje z uzasadnieniem, do zrobienia), testami lub
  ich ograniczeniami, diffem i atomowym commitem.
- Domyślnie **nie twórz** etapów: spec + bilety + ADR + CHANGELOG pokrywają to samo bez dryfu.

## 10. Kopie i retencja

- Vault/backup to magazyn kopii, nie drugie repo i nie źródło kodu.
- Trzymaj jeden niezmienny baseline, ostatnie zatwierdzone checkpointy i ostatnie nieudane
  przebiegi. Nie kasuj baseline'u ani checkpointu potrzebnego niezakończonej migracji.
- Checkpoint przed pakietem zmian w binariach, nie przed każdym poleceniem. Rejestruj artefakty
  i hashe. Usuwaj tylko własne odtwarzalne artefakty i raportuj, co zostało.
