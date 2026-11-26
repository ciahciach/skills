# Wspólny słownik

Wersja bazy: `v1`. Źródło definicji: `ciahciach/skills`, `955a41a:GLOSSARY.md`.

### Issue tracker

**Issue tracker**:
Rejestr zgłoszeń repozytorium, np. GitHub Issues, Linear lub lokalne pliki Markdown.

**Issue**:
Pojedyncze zgłoszenie w Issue trackerze, np. błąd, zadanie lub specyfikacja.

**Decision ticket**:
W metodyce `wayfinder` zgłoszenie podrzędne mapy, które zawiera pytanie do rozstrzygnięcia, a nie fragment implementacji do wykonania.

**Triage role**:
Rola oznaczająca stan zgłoszenia w procesie triage. W konfiguracji skilli mapowanie ról na etykiety danego Issue trackera znajduje się w `docs/agents/triage-labels.md`.

### Kilo Code w VS Code

**Kilo**:
W kontekście pracy w VS Code rozszerzenie Kilo Code. Kilo CLI to osobne środowisko; wynik z CLI nie dowodzi działania rozszerzenia.

**Agent Manager**:
Część rozszerzenia Kilo do przeglądania i zarządzania sesjami i worktree. `agent_manager` to nazwa narzędzia, nie nazwa sesji.

**Sesja**:
Osobny wątek pracy Kilo z własnym kontekstem, niezależny od katalogu roboczego. Świeża sesja nie jest istniejącą sesją skróconą przez `compact`.

**Subagent**:
Wykonawca oddelegowany przez inną sesję, wewnętrzny albo uruchomiony jako osobna sesja, także w nowym worktree. Zwraca wynik sesji zlecającej lub zostawia jej dostępny wynik.

**Swarm**:
Grupa wykonawców pracujących pod koordynacją sesji głównej.

**Worker**:
Pojedynczy wykonawca w swarmie. Subagent to pojęcie szersze, bo delegacja nie musi być częścią swarma.

**Worktree**:
Katalog roboczy Git powiązany z repozytorium. Nowy worktree w Agent Managerze to dodatkowy katalog roboczy zarządzany przez Agent Managera.

**`spawn`**:
Skill do startu sesji w Agent Managerze, w istniejącym katalogu roboczym Git albo w nowym, izolowanym worktree. Wewnętrzny `task` to osobny mechanizm.

**Handoff**:
Przekazanie tej samej pracy świeżej sesji Kilo w tym samym katalogu roboczym Git, bez zmiany brancha. Jeżeli następca ma edytować, potrzebne jest także jawne przejęcie zapisu.

**Zakres zapisu**:
Pliki lub artefakty, które wykonawca może zmieniać w ramach zlecenia. Techniczny dostęp nie poszerza uzgodnionego zakresu.

**Przejęcie zapisu**:
Jawne objęcie tego samego zakresu zapisu przez następcę po zwolnieniu go przez poprzednika i sprawdzeniu stanu pracy. To uzgodnienie między sesjami, nie techniczna blokada Kilo.

**Permission**:
Natywna zgoda Kilo na konkretną operację lub wywołanie narzędzia. Nie jest akceptacją wyniku ani zgodą na następny krok.

**Pytanie Kilo**:
Pytanie merytoryczne w interfejsie Kilo, które wstrzymuje sesję do czasu odpowiedzi. Zgoda na operację to osobne permission.

**Wydanie skilla**:
Opublikowana, identyfikowalna wersja skilla. Publikacja nie dowodzi, że dana sesja jej użyła.

**Załadowana kopia skilla**:
Kopia skilla faktycznie użyta w danej sesji. Może pochodzić z wydania albo np. z lokalnego katalogu skilli.

**Merge**:
Scalenie zmian Git do docelowej gałęzi. Nie jest wydaniem, wdrożeniem ani akceptacją kopii skoroszytu.

**Issue gotowe do startu**:
Zgłoszenie ze zleconego zakresu, które spełnia warunki startu i nie ma jeszcze wykonawcy.

**Kolejka gotowych issue**:
Zgłoszenia gotowe do startu, które można uruchomić w granicach dostępnych slotów, bez narzuconej kolejności.

**Odblokowane issue**:
Zgłoszenie, z którego spadła blokada wynikająca z innego zgłoszenia. Może nadal nie spełniać innych warunków startu.

### Excel

**Excel**:
Program Microsoft Excel i jego środowisko pracy, nie nazwa konkretnego pliku.

**Skoroszyt**:
Konkretny plik Excela, np. `.xlsx` lub `.xlsm`, a nie program Excel ani pojedynczy arkusz. Jeżeli cechy pliku mają znaczenie, opisz je wprost.

**Binarka**:
Potoczna nazwa pliku skoroszytu lub dodatku Excela. W zgłoszeniu nazwij jego rolę, np. skoroszyt bazowy albo kopia robocza.

**Plik formularzowy**:
Binarny plik `.frx` towarzyszący eksportowanemu VBA UserForm, odrębny od pliku `.frm` i skoroszytu.

**Backend skoroszytu**:
Wewnętrzna logika i elementy techniczne, z których użytkownik końcowy nie korzysta bezpośrednio, np. zapytania Power Query, VBA i formuły pomocnicze. COM i MCP nie należą do backendu skoroszytu.

**Sposób komunikacji z Excelem**:
Interfejs lub narzędzie, przez które agent przekazuje operacje do Excela lub odczytuje wyniki, np. bezpośredni COM albo serwer Excel MCP. To nie backend skoroszytu ani środowisko wykonania.

**Frontend skoroszytu**:
Interfejs użytkownika, w którym użytkownik końcowy pracuje ze skoroszytem. Widoczny element obsługi należy do frontendu, ukryta za nim logika do backendu.

**GUI**:
Interaktywny graficzny interfejs użytkownika. W Excelu może znajdować się np. w arkuszu lub w oknie UserForm.

**UserForm**:
Natywny formularz VBA z interaktywnymi elementami, wyświetlany przez `.Show`. Nie jest nim podgląd HTML ani formularz w arkuszu.

**MsgBox**:
Wyskakujący komunikat VBA, wyświetlany przez `MsgBox`. Może zawierać przyciski odpowiedzi, ale nie jest UserForm.

**Kompilacja VBA**:
Jawne sprawdzenie kompilacji projektu w edytorze VBA (`VBE`), raportowane osobno od zapisania i wykonania kodu.

**Power Query**:
Funkcja Excela i, w kontekście skoroszytu, jego zapytania służące do transformacji danych. Kod zapytań nazywamy M.

**M**:
Język zapytań Power Query i kod napisany w tym języku. Zmiana M sama nie oznacza zmiany miejsca ładowania, połączenia ani odświeżenia wyników.

**Miejsce ładowania Power Query**:
Konfiguracja określająca, czy i dokąd trafia wynik zapytania, np. do arkusza lub Data Model. Zachowanie konkretnego połączenia lub tabeli wskazujemy osobno.

**Import M**:
Przeniesienie zmiany kodu M do zapytania w skoroszycie. W kontrolowanym imporcie sama edycja M nie obejmuje zmiany miejsca ładowania ani odświeżenia wyników.

**Refresh**:
Odświeżenie, czyli ponowne wykonanie zapytania i aktualizacja wyniku. Odświeżenie pojedynczego zapytania to nie to samo co `Refresh All`.

**Dry-run**:
Przebieg bez zapisu do skoroszytu, który pokazuje plik bazowy, planowane zmiany, elementy do zachowania i blokady. Nie dowodzi udanego importu ani nie daje zgody na zapis.

**Próba zapisu bez zmian**:
Zapis kopii skoroszytu bez zamierzonej edycji i sprawdzenie wpływu samego zapisu. To nie przebieg, w którym w ogóle nie zapisano pliku.

**Ponowny odczyt**:
Odczyt zapisanej kopii po zamknięciu i ponownym otwarciu. Potwierdza trwałość sprawdzanej zmiany, a nie np. wykonanie zapytania, którego kod odczytano.

**Baseline skoroszytu**:
Uzgodniony stan odniesienia do porównywania zmian. Baseline to stan, nie plik; zapis nowej kopii go nie zmienia.

**Punkt synchronizacji**:
Zapis powiązania zaakceptowanego stanu skoroszytu z odpowiadającym mu stanem źródeł w repozytorium. Samo sprawdzenie kopii nie przesuwa tego punktu.

**Eksport tekstowy skoroszytu**:
Czytelny i porównywalny zapis wybranej logiki i struktury skoroszytu, nie pełna kopia pliku.

**Skoroszyt bazowy**:
Konkretny plik wejściowy, z którego powstaje kopia do kontrolowanej zmiany. Kontrolowany import zapisuje do kopii, nie do pliku bazowego.

**Kopia robocza**:
Osobny plik przeznaczony do wykonania zleconej zmiany, przed akceptacją.

**Zweryfikowana kopia z wprowadzoną zmianą**:
Pełna kopia skoroszytu ze zmianą i wymaganymi dowodami jej weryfikacji. Nie jest automatycznie zaakceptowaną kopią.

**Zaakceptowana kopia**:
Kopia przyjęta przez uprawnionego odbierającego na podstawie dowodów. Akceptacja to nie podmiana pliku bazowego, publikacja ani przyznanie wyłączności zapisu.

**Kontrolowany import**:
Zastosowanie uzgodnionych zmian na osobnej kopii z weryfikacją zmian i elementów do zachowania. Dry-run, zapis, ponowny odczyt i akceptacja są osobnymi etapami.

**Integracja skoroszytu po merge**:
Przeniesienie już scalonych zmian z Git do kopii skoroszytu i weryfikacja na niej. „Po merge” określa kolejność, nie wyzwalacz ani zgodę.

**Wyłączność zapisu do skoroszytu**:
Osobno uzgodnione prawo jednego wykonawcy do zmieniania wskazanego skoroszytu podczas prac strukturalnych. To nie techniczna blokada otwartego pliku ani skutek akceptacji kopii.

### Wspólne

**Scaffold**:
Szkielet organizujący elementy artefaktu. Scaffold repozytorium to układ katalogów, plików i instrukcji; scaffold skoroszytu to szkielet pliku.

**Środowisko wykonania**:
Program lub środowisko, w którym faktycznie przebiegła operacja, np. desktopowy Excel na Windows, Kilo Code w VS Code lub przeglądarka.

**Użytkownik końcowy**:
Osoba korzystająca z produktu bez konieczności poznawania jego wewnętrznej logiki. To niekoniecznie osoba pracująca z agentem nad produktem.

**Zlecający**:
Osoba lub agent, który wyznacza zakres pracy i przekazuje go wykonawcy.

**Odbierający**:
Osoba lub agent uprawniony do oceny i akceptacji wyniku. Odbiorca produktu nie staje się przez to odbierającym.

**HITL**:
Human in the Loop, czyli udział człowieka w pracy. „HITL wymagany” oznacza, że krok czeka na decyzję lub czynność człowieka.

**Review**:
Ocena wskazanego artefaktu względem wymagań i standardów, odrębna od testów. Review kodu obejmuje konkretny diff względem konkretnej bazy, a nie późniejsze zmiany wpływające na ocenę.

**Weryfikacja**:
Sprawdzenie określonego zachowania lub wyniku i zebranie dowodu. Dowód potwierdza tylko to, co sprawdzono.

**Sprawdzenie wstępne**:
Sprawdzenie warunków rozpoczęcia pracy, np. dostępności narzędzia, stanu blokady lub wymaganej zgody. `Preflight` jest synonimem.

**Scenariusz próby**:
Opis czynności i oczekiwanego zachowania. Nie jest plikiem, repozytorium ani danymi użytymi do wykonania próby.

**Wynik próby**:
`PASS` oznacza zaobserwowane oczekiwane zachowanie, `FAIL` odstępstwo, `BLOCKED` przeszkodę w wykonaniu lub potwierdzeniu, a `N/A` niedotyczące kryterium. Pominięta próba to „nie wykonano”, nie `N/A`.

**Dowód z próby**:
Zapis obserwacji, który uzasadnia wynik, np. odczyt zapisanej formuły lub zdarzenie startu sesji. Zapis przyjęcia promptu nie dowodzi rozpoczęcia pracy.

**Odbiór**:
Ocena wyniku według uzgodnionych kryteriów, odrębna od zbierania dowodów. Gdy wymagana jest akceptacja człowieka, odbiór wymaga jego jawnej decyzji.
