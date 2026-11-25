# Inwentaryzacja skilli Kilo i Excel (#78)

Stan początkowy z 25.11.2026 dla [#78](https://github.com/ciahciach/skills/issues/78). Tabela zachowuje stan sprzed zmian profilu. Obowiązujący zakres po decyzji użytkownika jest na końcu raportu.

## Wniosek

Zachować bibliotekę. W zwykłej pracy dawać agentowi przede wszystkim krótkie wskazówki do routingu i weryfikacji; specjalistyczne recepty ładować po wyborze ścieżki albo jawnym wywołaniu. Do przyszłego wyłączenia w tym profilu są dwaj wskazani przez użytkownika kandydaci: `implement-wave` i `claude-handoff`. Pozostałych nie usuwać z powodu samego braku śladu użycia. `implement` zostaje na jawne wywołanie: w tym zgłoszeniu został faktycznie użyty.

- `implement-wave`: dubluje część koordynacji. Dla grafu zależności w Kilo używać `implement-spec`; do niezależnych zadań w obrębie jednej sesji, gdy podział ma sens, wystarczy `task`. To nie są zamienniki 1:1. Przed wyłączeniem poprawić odsyłacze w `ask-matt` i `co-dalej` oraz sprawdzić pozostałe komendy/odsyłacze. Skilla zachować w bibliotece.
- `claude-handoff`: uruchamia `claude --bg`, a więc nie jest ścieżką kontynuacji w Kilo VS Code. `kilo-handoff` służy do świeżej sesji w tym samym checkoutcie, a `handoff` do przekazania dokumentu bez uruchamiania sesji. Nie rozszerzać wyłączenia na te dwa skille.
- W Excelu `excel-router` jest punktem wejścia, nie dowodem zakwalifikowania backendu. `excel-mcp`, `excel-cli`, `excel-com-safe`, `passive-excel-audit`, `xlsx` i skille VBA powinny pozostać dostępne jako recepty dobierane do konkretnej operacji. Nie ładować kilku backendów „na wszelki wypadek”. Zob. [kwalifikacja #40](excel-route-qualification-40.md) oraz [router](../../skills/in-progress/excel-router/SKILL.md).

## Koszt i źródła

Kilo stosuje [ładowanie na żądanie](https://kilo.ai/docs/customize/skills): przy starcie w katalogu model widzi nazwę, opis i ścieżkę; pełna treść trafia do kontekstu po wywołaniu, np. przez `skill` lub komendę użytkownika. Sama instalacja nie ładuje całego `SKILL.md`. Nie należy dodawać pełnych recept do `instructions`, `AGENTS.md` ani reguł globalnych. `Jawnie` poniżej oznacza rekomendowany sposób użycia, a nie obecną blokadę modelu. Repozytoryjne flagi [wywoływania](../../.agents/invocation.md) opisują Claude Code i Codex; nie zakładamy, że ukrywają wpis w Kilo. W tej sesji `implement` i `claude-handoff` były widoczne mimo tych flag. Rozdzielenie komendy od automatycznego odkrywania wymaga osobnej próby w świeżym profilu Kilo, z kontrolą listy agenta i działania komendy.

Każda liczba to szacunek `ceil(liczba znaków / 4)`, nie pomiar modelu. `Start` liczy nazwę, spację i opis z pliku (zwinięte białe znaki); pomija ścieżkę i opakowanie. `Treść` liczy przycięty Markdown po frontmatterze, bez załączonych plików, wyników poleceń i opakowania narzędzia. Dla 65 widocznych skilli plikowych suma wynosi ok. **3 134** w metadanych i **80 324** w treści. Druga suma to rozmiar biblioteki, nie koszt startu. Usunięcie obu kandydatów z listy discovery zmniejszyłoby samą część nazwa + opis o ok. **49**; ich **1 886** tokenów treści już dziś nie stanowi stałego kosztu. Większy efekt dałoby skrócenie samych opisów `xlsx` i `agent-browser`, z zachowaniem rozróżniających je warunków wywołania.

Tabela obejmuje 66 pozycji widocznych w sesji `ses_ded4ee0c0ffec7MVZldix6wnBI`: 48 nazw z repo (stan początkowy `9799e0d`) i 18 spoza repo (w tym jedna wbudowana). Rozmiary liczone z plików `~/.agents/skills/<nazwa>/SKILL.md`, dla `_TEMPLATE` z `~/.kilo/skills/_TEMPLATE/SKILL.md`, nie z manifestu wydania. To pomiar lokalnych, zmiennych kopii bez archiwizacji ich treści; sam commit raportu nie odtwarza stanu profilu. Gwiazdka przy nazwie oznacza pozycję spoza checkoutu, a nie rekomendację tłumaczenia zewnętrznego skilla. `self-improving-agent` znaleziono na dysku, ale nie na liście narzędzia tej sesji: ok. **88 / 6 529**, poza sumą i bez wniosku o przyczynie niewidoczności. `kilo-config` jest wbudowany; kosztu nie liczono z pliku, więc `n/d` nie oznacza zera.

## Dowody użycia

`kilo_local_recall` przeszukał 133 sesje tego projektu i jego worktree (zapytania m.in. `Base directory for this skill`, `<skill_content`, `excel-router` i `implement-wave`), ale nie zwraca wszystkich wywołań ani ich wyników. Nie obejmuje innych projektów. Trafienie nazwy w instrukcji, README czy dyskusji nie jest wywołaniem. Nie da się tym źródłem rzetelnie policzyć użycia każdego skilla osobno przez użytkownika i przez agentów.

| Kto | Co da się potwierdzić | Czego to nie dowodzi |
| --- | --- | --- |
| Użytkownik | Treść `implement` w wiadomościach dla #22, #26, #40 i #78; `wayfinder` dla #6, #8, #10, #14 i #43 (sygnatura `Base directory for this skill`). | Nie odtwarza kliknięcia ani tego, ile razy skill uruchomiono globalnie. |
| Agent: udane wywołanie | W tej sesji `tdd`, `kilo-config`, `code-review` i `co-dalej`; [#51](kilo-vscode-acceptance-51.md) dokumentuje udane wywołanie `kilo-handoff`, ale załadowano starszą lokalną kopię. | Nie gwarantuje tej samej kopii w świeżej sesji ani zgodności z wydaniem. |
| Agent: odczyt i nieudana próba | [#40](excel-route-qualification-40.md) dokumentuje użycie `excel-router` z pliku repo i próbę Direct COM; historyczny test [#59](https://github.com/ciahciach/skills/issues/59) (`ses_df137c8dbffegvvV7i8jc7pKMS`) odnotował nieudane `skill(excel-router)`. | Odczyt pliku nie jest udanym wywołaniem narzędzia `skill`; próba COM nie potwierdza całego zakresu Excela. |
| Brak potwierdzenia | Wzmianki o `implement-wave` nie potwierdziły jego wywołania; dla `claude-handoff` brak zweryfikowanego użycia w Kilo. | Nie oznacza „nigdy nie użyto”. Wyłączenie jest propozycją użytkownika i ma uzasadnienie w procesie. |

## Lista

**Zwykła**: pasuje do typowego przebiegu tego repo, agent może dobrać po opisie. **Jawnie**: nie ładować na podstawie szerokiego triggera. Dla narzędzi Excel wystarczy konkretne wskazanie routera i właściwa zgoda na operację; dla `spawn` i `kilo-handoff` potrzebne jest polecenie użytkownika. **Poza**: nie jest używane jako element docelowej ścieżki tego repo/profilu; zachować w bibliotece.

**Status dowodu jest niezależny od rekomendacji.** Dla skilli nazwanych w tabeli „Dowody użycia” obowiązuje podany tam status. Dla każdej pozostałej pozycji: **brak potwierdzenia wywołania w materiale użytym w tym audycie**. Opisy w ostatniej kolumnie to przypadki zastosowania lub powody odłożenia skilla, nie twierdzenia o zaobserwowanej częstotliwości.

| Skill | Start | Treść | Rekomendacja | Przypadek lub powód |
| --- | ---: | ---: | --- | --- |
| `_TEMPLATE`* | 28 | 128 | Poza | Szablon do autorstwa; nie jest instrukcją do wykonania zadania. |
| `agent-browser`* | 235 | 572 | Jawnie | Przy odbiorze HTML lub UI; nie do operacji na skoroszycie ani do rutynowego `gh`. |
| `ask-matt` | 23 | 3594 | Jawnie | Mapa wyboru workflow, gdy kilka komend pasuje; nie czytać w każdym bilecie. |
| `board-etiquette`* | 34 | 170 | Jawnie | Tylko gdy review lub wspólna praca faktycznie korzysta z tablicy. |
| `bounded-runner`* | 55 | 226 | Poza | Procedura właściwa dla `versuni-search-ecosystem`, nie dla testów tego katalogu. |
| `chief-of-staff` | 23 | 1145 | Jawnie | Długotrwały cel w jednej sesji; nie zamiast `implement-spec` dla zwykłego grafu zgłoszeń. |
| `claude-handoff` | 28 | 299 | Poza | Kandydat do wyłączenia w Kilo; ścieżka `claude --bg`. |
| `co-dalej` | 20 | 668 | Zwykła | Wskazanie jednego następnego kroku po zakończeniu biletu. |
| `code-review` | 108 | 1721 | Zwykła | Zgodność diffu ze standardami i kryteriami zgłoszenia przed commitem. |
| `codebase-design` | 71 | 1439 | Jawnie | Przy projektowaniu granicy między routerem a backendem; zbędny przy samym audycie. |
| `diagnosing-bugs` | 43 | 2115 | Zwykła | Rozbieżność między zainstalowaną a załadowaną wersją skilla lub regresja skryptu. |
| `domain-modeling` | 42 | 960 | Jawnie | Porządkowanie terminologii w `GLOSSARY.md` i decyzji, nie zwykły przegląd listy. |
| `excel-cli`* | 71 | 1204 | Jawnie | Recepta `excelcli` po wyborze i kwalifikacji backendu; sam preflight #40 nie wystarcza. |
| `excel-com-safe` | 52 | 1433 | Jawnie | Wybrany Direct COM na kopii, np. syntetyczna zmiana formuły #40 lub UserForm #22. |
| `excel-mcp`* | 110 | 1485 | Jawnie | Tylko dla potwierdzonych narzędzi MCP i zakresu operacji wskazanego przez router. |
| `excel-router` | 48 | 1177 | Zwykła | Pierwsza klasyfikacja zadania Excel: eksport tekstowy, odczyt pasywny lub operacja na pliku. |
| `find-skills`* | 79 | 1278 | Jawnie | Poszukiwanie brakującej recepty; nie do katalogowania lokalnych kopii. |
| `frontend-design`* | 55 | 2269 | Jawnie | Projektowanie demonstratora HTML, np. podglądu UserForm, nie automatyzacja Excela. |
| `git-guardrails-claude-code` | 68 | 504 | Poza | Hooki dla Claude Code, nie mechanizm uprawnień Kilo. |
| `granica` | 14 | 674 | Jawnie | Wybór między kontynuacją, kompaktowaniem i przekazaniem sesji. |
| `grill-me` | 15 | 59 | Jawnie | Stres-test decyzji projektowej bez tworzenia dokumentacji. |
| `grill-with-docs` | 31 | 66 | Jawnie | Wywiad, który równocześnie aktualizuje słownik lub zapis decyzji. |
| `grilling` | 41 | 1014 | Zwykła | Wspólna procedura wywiadu dla skilli `grill-*`, nie zastępuje wyboru przez użytkownika. |
| `handoff` | 24 | 182 | Jawnie | Przenośny dokument stanu, gdy nie trzeba uruchamiać nowej sesji. |
| `implement` | 18 | 255 | Jawnie | Realizacja pojedynczego zgłoszenia, m.in. #40 i #78. |
| `implement-spec` | 29 | 798 | Jawnie | Graf zgłoszeń, oddzielne worktree i PR-y; odbiór runtime opisany jako zablokowany w #51. |
| `implement-wave` | 21 | 1587 | Poza | Kandydat do wyłączenia; osobna orkiestracja fali nie jest preferowaną ścieżką Kilo. |
| `improve-codebase-architecture` | 39 | 1593 | Jawnie | Przekrojowy raport HTML o granicach modułów, nie mała korekta dokumentu. |
| `kilo-config`* | n/d | n/d | Zwykła | Diagnoza, skąd VS Code ładuje skille, komendy i konfigurację. |
| `kilo-handoff` | 51 | 2296 | Jawnie | Kontynuacja w tym samym checkoutcie po wyraźnym zleceniu; dowód starszej kopii w #51. |
| `kilo-skill-authoring`* | 61 | 756 | Jawnie | Utrwalenie powtarzanej procedury w formacie Kilo po akceptacji, nie w ramach selekcji. |
| `loop-me` | 22 | 578 | Jawnie | Wywiad o nowym workflow; pozostawić jako opcję zamiast automatycznie uruchamiać wywiad. |
| `migrate-to-shoehorn` | 47 | 644 | Poza | Brak takiej migracji TypeScript w bieżących testach repo. |
| `msg-attachments`* | 43 | 237 | Jawnie | Wyjątek dla zamówienia z załącznikiem Outlook `.msg`; nie zwykły plik Excel. |
| `passive-excel-audit`* | 46 | 241 | Jawnie | Odczyt formuł, nazw lub zapytań bez uruchamiania Excela, gdy router wskaże tę klasę. |
| `powerbi-mcp`* | 66 | 1599 | Jawnie | Gdy zadanie przechodzi do modelu Power BI; nie jako recepta dla modelu Excela. |
| `pr` | 8 | 1014 | Zwykła | Opis PR z zakresem zmiany, dowodami i ograniczeniami weryfikacji. |
| `prototype` | 48 | 933 | Jawnie | Prototyp na próbce syntetycznej przed zmianą procedury lub UserForm. |
| `research` | 62 | 258 | Jawnie | Osobne zlecenie zbadania runtime/API i utrwalenia dowodów. |
| `retro` | 13 | 1114 | Jawnie | Retrospektywa kosztownej sesji, nie codzienna walidacja. |
| `retrofit-repo` | 21 | 1167 | Jawnie | Audyt i plan wdrożenia standardów w kolejnym repo. |
| `scaffold-exercises` | 56 | 834 | Poza | Bieżąca praca nie wymaga struktury kursu i ćwiczeń. |
| `setup-excel-repo` | 27 | 1035 | Jawnie | Pierwsza konfiguracja wersjonowania logiki skoroszytów w nowym repo. |
| `setup-matt-pocock-skills` | 52 | 3632 | Jawnie | Jednorazowy setup trackera i dokumentacji, nie na każdy start. |
| `setup-pre-commit` | 64 | 494 | Jawnie | Opcjonalna instalacja hooków przy osobnym zleceniu; audyt ich nie zmienia. |
| `setup-ts-deep-modules` | 52 | 1816 | Poza | Brak modułów TypeScript wymagających `dependency-cruiser` w tym repo. |
| `skill-creator`* | 84 | 8156 | Jawnie | Zmiana zachowania skilla i ewaluacje triggerów, nie samo czytanie katalogu. |
| `software-factory` | 29 | 1483 | Jawnie | Projektowanie całej automatyzacji, nie obsługa pojedynczego worktree. |
| `spawn` | 47 | 1580 | Jawnie | Nowa widoczna sesja lub worktree dopiero na polecenie użytkownika. |
| `tdd` | 39 | 860 | Zwykła | Test zachowania skryptu importu/eksportu na uzgodnionym publicznym interfejsie. |
| `teach` | 17 | 2388 | Jawnie | Lekcja używania workflow dla członka zespołu, nie realizacja zadania. |
| `to-questionnaire` | 27 | 684 | Jawnie | Gdy decyzja o procesie wymaga danych od innego właściciela. |
| `to-spec` | 40 | 828 | Jawnie | Zapis decyzji w specyfikacji na trackerze po ustaleniu wymagań. |
| `to-tickets` | 65 | 1473 | Jawnie | Podział specyfikacji na zgłoszenia z zależnościami. |
| `triage` | 36 | 1706 | Jawnie | Klasyfikacja ticketów i przygotowanie briefów według etykiet repo. |
| `vba-compile-cycle`* | 44 | 362 | Jawnie | Weryfikacja zmiany `.bas`, `.cls`, `.frm` lub logiki UserForm. |
| `vba-error-events-team`* | 20 | 462 | Jawnie | Zdarzenia skoroszytu i sprzątanie po błędach; zbędny przy eksporcie pasywnym. |
| `vba-objectmodel-performance`* | 31 | 451 | Jawnie | Masowe odczyty/zapisy przez VBA; nie dla pojedynczej formuły. |
| `wait-what` | 15 | 69 | Jawnie | Ponowne wyjaśnienie, gdy opis procesu nie był czytelny. |
| `wayfinder` | 52 | 3298 | Jawnie | Mapa decyzji dla dużego workflow Excel; ślady jawnych wywołań istnieją. |
| `wizard` | 80 | 942 | Jawnie | Czynności człowieka przy konfiguracji poświadczeń lub ręcznym wdrożeniu. |
| `writing-beats` | 32 | 1166 | Poza | Etap narracji tekstu, nie procedura pracy z kodem i skoroszytami w tym repo. |
| `writing-for-agents` | 31 | 2683 | Zwykła | Edycja instrukcji i opisów skilli jest podstawowym zadaniem tego repo. |
| `writing-fragments` | 19 | 856 | Poza | Zbieranie fragmentów do artykułu, nie audyt lub realizacja zgłoszeń. |
| `writing-shape` | 23 | 1441 | Poza | Redakcja artykułu, nie specyfikacja operacji Excel ani proces Kilo. |
| `xlsx`* | 239 | 2173 | Jawnie | Recepta dla pracy z plikiem tabelarycznym po decyzji routera, nie dla samego opisu formuły. |

## Decyzja użytkownika

- Wyłączyć dla agenta w osobistym profilu Kilo (`permission.skill: deny`): `implement-wave`, `claude-handoff`, `git-guardrails-claude-code`, `granica`, `migrate-to-shoehorn`, `powerbi-mcp`, `setup-ts-deep-modules`. Katalog ręcznych komend Kilo 7.8.32 nadal je pokazuje. Zachowano pliki skilli i ustawienia serwera MCP Power BI.
- Ustawić `/handoff` w tym profilu jako wejście do `kilo-handoff`, bez zmiany jego kontroli zgody i przekazywania zapisu. Przenośny dokument zachować jako `/handoff:skill` przy kolizji nazw w Kilo.
- Nie tłumaczyć skilli. Zastąpić jedynie wymagania prostego angielskiego prostym polskim w odpowiedziach `wait-what` i raporcie `improve-codebase-architecture`, zachowując słownictwo techniczne i słownik projektu.
