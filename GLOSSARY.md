# Matt Pocock Skills

Repozytorium skilli dla agentów, z konwencjami pracy w Kilo Code w VS Code i ze skoroszytami Excela. Słownik ustala nazwy używane w issue i instrukcjach skilli.

## Language

### Issue tracker

**Issue tracker**:
Rejestr zgłoszeń repozytorium, np. GitHub Issues, Linear lub lokalne pliki Markdown w `.scratch/`. Skille `to-tickets`, `to-spec` i `triage` czytają i zapisują do tego rejestru.
_Avoid_: backlog manager, backlog backend, issue host

**Issue**:
Pojedyncze zgłoszenie w **Issue trackerze**, np. bug, task, spec lub część pracy wydzielona przez `to-tickets`.
_Avoid_: ticket i bilet (wyjątki to cytaty z innych systemów, które nazywają je ticketami, albo dla **Decision ticket**, patrz niżej)

**Decision ticket**:
Jednostka w `wayfinder`: potomny **Issue** elementu `wayfinder:map` zawierające *pytanie*, na które odpowiedzią jest decyzja, a nie fragment kodu do wykonania. To właśnie określenie **decyzja** odróżnia ten dokument od zgłoszenia dotyczącego wdrożenia; w `wayfinder` pojawia się najpierw ten termin, a następnie używa się słowa "ticket".
_Avoid_: bilet

**Triage role**:
Standardowa etykieta state-machine przypisywana do **Issue** podczas triage (np. `needs-triage`, `ready-for-afk`). Każda rola jest powiązana z rzeczywistym ciągiem znaków etykiety w **Issue tracker** za pośrednictwem pliku `docs/agents/triage-labels.md`.

### Kilo Code w VS Code

**Kilo**:
W tym repo rozszerzenie Kilo Code do VS Code. Kilo CLI to inne środowisko; wynik z CLI nie jest dowodem działania rozszerzenia.
_Avoid_: „Kilo” w znaczeniu Kilo CLI; gdy chodzi o CLI, nazwij je wprost.

**Agent Manager**:
Część Kilo, w której widać sesje i worktree i można nimi zarządzać. `agent_manager` to nazwa narzędzia, nie nazwa sesji.

**Sesja**:
Osobny wątek pracy w Kilo z własnym kontekstem, niezależny od katalogu roboczego. Świeża sesja jest nową sesją, nie skróconą przez `compact` sesją istniejącą.

**Subagent**:
Wykonawca oddelegowany przez inną sesję, wewnętrzny albo uruchomiony jako osobna sesja, również w nowym worktree. Raportuje do sesji zlecającej lub zostawia jej dostępny wynik.

**Swarm**:
W Kilo grupa wykonawców pracujących pod koordynacją sesji głównej.

**Worker**:
Pojedynczy wykonawca w **swarmie**. **Subagent** to pojęcie szersze: delegacja nie musi być częścią swarma.

**Worktree**:
Katalog roboczy Git powiązany z repozytorium. W kontekście `spawn` nowy worktree to dodatkowy katalog roboczy Git utworzony i zarządzany przez **Agent Managera**.

**`spawn`**:
Skill Kilo do startu sesji w **Agent Managerze**, w istniejącym katalogu roboczym Git albo w nowym, izolowanym **worktree**. Wewnętrzny `task` to osobny mechanizm.

**Handoff**:
Przekazanie kontekstu tej samej pracy świeżej sesji Kilo w tym samym katalogu roboczym Git, bez zmiany brancha, przez `kilo-handoff`, odpowiednik `claude-handoff` dla Kilo. Gdy następca ma edytować, handoff obejmuje jawne **przejęcie zapisu**, nie tylko dostarczenie notatki lub promptu.
_Avoid_: „ten sam checkout”; pisz „ten sam katalog roboczy Git, bez zmiany brancha”.

**Zakres zapisu**:
Pliki lub artefakty, które wykonawca może zmieniać w ramach zlecenia. Techniczny dostęp do całego repozytorium nie poszerza uzgodnionego zakresu.

**Przejęcie zapisu**:
Jawne objęcie tego samego **zakresu zapisu** przez następcę po zwolnieniu go przez poprzednika i sprawdzeniu stanu pracy. Przed przejęciem następca ma tylko odczyt; to uzgodnienie między sesjami, nie techniczna blokada Kilo.

**Permission**:
Natywna zgoda Kilo na konkretną operację lub wywołanie narzędzia. Nie oznacza merytorycznej akceptacji wyniku ani zgody na kolejny krok.

**Pytanie Kilo**:
Pytanie merytoryczne pokazane w interfejsie Kilo, które wstrzymuje sesję do czasu odpowiedzi. Zgoda na operację lub wywołanie narzędzia to osobne **permission**.

**Wydanie skilla**:
Opublikowana, identyfikowalna wersja skilla. Opublikowanie wydania nie dowodzi, że Kilo użyło go w danej sesji.

**Załadowana kopia skilla**:
Kopia skilla, której Kilo faktycznie użyło w danej sesji. Może pochodzić z wydania albo z innego źródła, np. z lokalnego katalogu skilli.

**Merge**:
Scalenie zmian Git do docelowej gałęzi. Nie jest wydaniem, wdrożeniem ani zmianą lub akceptacją kopii skoroszytu.

**Issue gotowe do startu**:
Issue ze zleconego zakresu, które spełnia warunki startu i nie ma jeszcze wykonawcy.

**Kolejka gotowych issue**:
Kilka **issue gotowych do startu**, które można uruchomić równolegle w granicach dostępnych slotów, bez narzuconej kolejności.
_Avoid_: frontier

**Odblokowane issue**:
Issue, z którego spadła blokada wynikająca z innego issue. Może nadal nie spełniać innych warunków startu.

**Testowy graf issue A/B/C**:
Układ trzech issue do próby koordynacji w Kilo: A i B mogą ruszyć równolegle, a C czeka na potwierdzony merge A.
_Avoid_: samo A/B/C bez wskazania, że chodzi o graf issue

### Excel

**Excel**:
Program Microsoft Excel i jego środowisko pracy. Excel otwiera i obsługuje skoroszyty; nie jest nazwą konkretnego pliku.

**Skoroszyt**:
Konkretny plik Excela, np. `.xlsx` lub `.xlsm`, a nie program Excel ani pojedynczy arkusz. Rodzaj pliku opisujemy wprost, np. „`.xlsx` z wynikiem zapytania ładowanym do tabeli w arkuszu `Raport`” albo „dodatek `.xlam`”.
_Avoid_: profil skoroszytu jako zamiennik opisu konkretnych cech pliku

**Binarka**:
Potoczna nazwa pliku skoroszytu lub dodatku Excela, np. `.xlsx`, `.xlsm`, `.xlsb` lub `.xlam`. W issue używamy konkretnej roli pliku, np. **skoroszyt bazowy**, **kopia robocza** albo **zaakceptowana kopia**.

**Plik formularzowy**:
Binarny plik `.frx` towarzyszący eksportowanemu VBA **UserForm**, odrębny od `.frm` i pliku skoroszytu.
_Avoid_: „binarka” jako nazwa pliku `.frx`.

**Backend skoroszytu**:
Wewnętrzna logika i elementy techniczne, z których użytkownik końcowy nie korzysta bezpośrednio, np. zapytania Power Query, VBA, formuły pomocnicze i arkusze techniczne. COM i MCP nie są częścią backendu skoroszytu.

**Sposób komunikacji z Excelem**:
Interfejs lub narzędzie, przez które agent przekazuje operacje do Excela lub odczytuje ich wyniki, np. bezpośredni COM albo konkretny serwer Excel MCP. To nie **backend skoroszytu** ani **środowisko wykonania**.
_Avoid_: backend Excela w odniesieniu do COM lub MCP

**Frontend skoroszytu**:
Interfejs użytkownika (UI), w którym użytkownik końcowy pracuje ze skoroszytem. Widoczny element obsługi należy do frontendu, a ukryta za nim logika do backendu.

**GUI**:
Interaktywny graficzny interfejs użytkownika. Może znajdować się w arkuszu lub w oknie **UserForm**.

**UserForm**:
Natywny formularz VBA z interaktywnymi elementami, wyświetlany przez `.Show`. Nie jest nim podgląd HTML ani formularz zbudowany bezpośrednio w arkuszu.

**Warianty formularza A/B/C**:
Trzy opcje wyglądu lub zachowania formularza Excel, pokazywane jako podglądy HTML lub natywne **UserForm**. Akceptacja podglądu HTML nie potwierdza działania interakcji w Excelu.
_Avoid_: samo A/B/C bez wskazania, że chodzi o warianty formularza

**MsgBox**:
Wyskakujący komunikat VBA, wyświetlany przez `MsgBox`. Może zawierać przyciski odpowiedzi, ale nie jest **UserForm**.

**Kompilacja VBA**:
Jawne sprawdzenie kompilacji projektu w edytorze VBA (`VBE`). Raportujemy ją osobno od zapisania kodu i wykonania kodu w Excelu.

**Power Query**:
Funkcja Excela i, w kontekście pracy nad skoroszytem, jego zapytania służące do transformacji danych. Skrót `PQ` może potocznie oznaczać też kod zapytania, ale w precyzyjnym opisie kodu używamy **M**.
_Avoid_: pisownia `powerquery` poza identyfikatorami.

**M**:
Język zapytań Power Query i kod napisany w tym języku. Zmiana M nie oznacza sama w sobie zmiany miejsca ładowania, połączenia ani odświeżenia wyników.

**Miejsce ładowania Power Query**:
Konfiguracja określająca, czy i dokąd trafia wynik zapytania, np. do arkusza, do Data Model albo bez ładowania wyniku. „Konfiguracja ładowania” jest synonimem; zachowanie konkretnego połączenia lub tabeli wskazujemy osobno.

**Import M**:
Przeniesienie zmiany kodu **M** do zapytania w skoroszycie. Sam import nie zmienia miejsca ładowania ani nie odświeża wyników; zapisany kod można zweryfikować bez wykonania zapytania.

**Refresh**:
Odświeżenie, czyli ponowne wykonanie zapytania i aktualizacja jego wyniku. W issue rozróżniamy odświeżenie pojedynczego zapytania od `Refresh All`.

**Dry-run**:
Próba bez zapisu do skoroszytu, która pokazuje plik bazowy, planowane zmiany, elementy do zachowania i blokady. Wynik dry-runu nie jest dowodem udanego importu ani zgodą na zapis.

**Próba zapisu bez zmian**:
Zapis kopii skoroszytu bez zamierzonej edycji i sprawdzenie, czy sam zapis zmienił istotne elementy. Nie oznacza przebiegu, w którym w ogóle nie zapisano pliku.
_Avoid_: `no-op save` w polskich opisach; gdy niczego nie zapisano, raportuj „bez zmian”.

**Ponowny odczyt**:
Odczyt zapisanej kopii po jej zamknięciu i ponownym otwarciu (`reopen/readback`). Potwierdza trwałość sprawdzanej zmiany, a nie np. wykonanie zapytania, którego kod odczytano.

**Baseline skoroszytu**:
Uzgodniony stan odniesienia, względem którego porównujemy zmianę. Baseline to stan, nie plik; sam zapis nowej kopii go nie zmienia.

**Punkt synchronizacji**:
Zapis powiązania zaakceptowanego stanu skoroszytu z odpowiadającym mu stanem źródeł w repozytorium. Samo utworzenie i sprawdzenie kopii nie przesuwa punktu synchronizacji.

**Eksport tekstowy skoroszytu**:
Czytelny i porównywalny zapis wybranej logiki i struktury skoroszytu. Nie jest pełną kopią binarki ani sam w sobie nie pozwala odtworzyć wszystkich jej elementów.

**Skoroszyt bazowy**:
Konkretny plik wejściowy, z którego powstaje kopia do kontrolowanej zmiany. W tym workflow import zapisuje do kopii, nie do pliku bazowego.

**Kopia robocza**:
Osobny plik przeznaczony do wykonania zleconej zmiany, przed akceptacją.

**Zweryfikowana kopia z wprowadzoną zmianą**:
Pełna kopia binarki ze zmianą z issue i wymaganymi dowodami jej weryfikacji. Nie jest automatycznie **zaakceptowaną kopią**, a sam zapis nie wystarcza, gdy wymagany jest dowód działania.

**Zaakceptowana kopia**:
Kopia przyjęta przez uprawnionego **odbierającego**, człowieka lub agenta, na podstawie dowodów spełnienia kryteriów odbioru. Akceptacja nie jest podmianą pliku bazowego, publikacją ani przyznaniem wyłącznego zapisu.

**Kontrolowany import**:
Zastosowanie uzgodnionych zmian na osobnej kopii skoroszytu, z udokumentowaną weryfikacją zarówno zmian, jak i elementów, które mają pozostać bez zmian. **Dry-run**, zapis, **ponowny odczyt** i akceptacja są osobnymi etapami.

**Integracja skoroszytu po merge**:
Etap, w którym zmiany już scalone w Git trafiają do kopii skoroszytu i są na niej weryfikowane. „Po merge” określa kolejność, nie automatyczny wyzwalacz ani zgodę na operację.

**Wyłączność zapisu do skoroszytu**:
Osobno uzgodnione prawo jednego wykonawcy do zmieniania wskazanego skoroszytu podczas prac strukturalnych. Nie wynika z akceptacji kopii i nie jest techniczną blokadą pliku otwartego w Excelu.

### Wspólne

**Scaffold**:
Szkielet organizujący elementy danego artefaktu. **Scaffold repozytorium Excel** to układ katalogów, plików i instrukcji niezależny od obecności binarki; **scaffold skoroszytu** to szkielet samego pliku.

**Środowisko wykonania**:
Program lub środowisko, w którym faktycznie przebiegła operacja, np. desktopowy Excel na Windows, Kilo Code w VS Code lub przeglądarka. W kryteriach odbioru nazywamy je wprost, np. „sprawdzone w działającym desktopowym Excelu”.
_Avoid_: runtime w nowej prozie

**Użytkownik końcowy**:
Odbiorca, dla którego powstaje skoroszyt i który korzysta z niego bez znajomości wewnętrznej logiki. Gdy „użytkownik” może oznaczać też osobę rozmawiającą z Kilo, wskazujemy jej faktyczną rolę, np. deweloper.

**Zlecający**:
Osoba lub agent, który wyznacza zakres pracy i przekazuje go wykonawcy. Sesja główna zlecająca pracę **subagentowi** również pełni tę rolę.

**Odbierający**:
Osoba lub agent uprawniony do oceny i akceptacji wyniku. **Odbiorca** korzysta z produktu; nie staje się przez to automatycznie odbierającym.

**HITL**:
Human in the Loop, czyli udział człowieka w przebiegu pracy. „HITL wymagany” oznacza, że krok czeka na decyzję lub czynność człowieka ze względu na regułę, ograniczenie narzędzia lub skilla albo prostsze wykonanie przez człowieka, np. ręczne logowanie do SharePoint przed odświeżeniem.

**Review**:
Ocena wskazanego artefaktu, np. planu importu lub diffu formuł, względem wymagań i standardów, odrębna od uruchomienia testów. Review kodu dotyczy konkretnego diffu względem konkretnej bazy i nie obejmuje późniejszych zmian wpływających na ocenę.

**Weryfikacja**:
Sprawdzenie określonego zachowania lub wyniku i zebranie dowodu. Dowód potwierdza tylko to, co sprawdzono.

**Sprawdzenie wstępne**:
Sprawdzenie warunków rozpoczęcia pracy, np. dostępności Excela, blokady pliku lub wymaganej zgody. `Preflight` jest synonimem; w polskich opisach preferujemy „sprawdzenie wstępne”.

**Scenariusz próby**:
Opis tego, co robimy i jakiego zachowania oczekujemy, np. C startuje po merge A, mimo że B nadal trwa. Scenariusz to nie skoroszyt, repozytorium ani dane użyte do wykonania próby.
_Avoid_: `fixture`; wejście do próby nazwij wprost, np. „skoroszyt testowy”, „repozytorium testowe” lub „dane testowe”.

**Wynik próby**:
`PASS` oznacza zaobserwowane oczekiwane zachowanie, `FAIL` odstępstwo od oczekiwań, `BLOCKED` przeszkodę uniemożliwiającą wykonanie lub potwierdzenie, a `N/A` kryterium, które nie dotyczy przypadku. W raporcie po polsku opisujemy, co zaszło; pominiętą próbę oznaczamy „nie wykonano”, nie `N/A`.

**Dowód z próby**:
Konkretny zapis obserwacji, np. odczyt zapisanej formuły lub zdarzenie startu sesji, który pozwala uzasadnić wskazany wynik. Zapis przyjęcia promptu nie jest dowodem rozpoczęcia pracy.
_Avoid_: samo „sprawdzone” albo ogólna „kwalifikacja operacji”; pisz „Sprawdziliśmy X na Y, używając Z. Nie sprawdziliśmy W”.

**Odbiór**:
Ocena wyniku według uzgodnionych kryteriów, odrębna od zbierania dowodów weryfikacji. Jeżeli wymagana jest akceptacja człowieka, odbiór wymaga jego jawnej decyzji.

## Relacje

- Rejestr zgłoszeń (**Issue tracker**) zawiera wiele zgłoszeń (**Issue**).
- Zgłoszenie (**Issue**) ma jedną **Triage role** w danym momencie.
- **Decision ticket** jest **Issue**, zgłoszeniem , elementem podrzędnym wobec `wayfinder:map`.
- **Merge** scala branch lub commity z **worktree**, nie sam katalog.

## Rozstrzygnięte niejednoznaczności

- Termin "backlog" był wcześniej używany zarówno w odniesieniu do *narzędzia* (*tool*) przechowującego zgłoszenia, jak i do *zbioru zadań* (*body of work*) w nim zawartych. Rozwiązane: narzędzie to **Issue tracker**; termin "backlog" nie jest już używany jako termin dziedzinowy.
- "backlog backend" / "backlog manager". Rozwiązano: polączono z **Issue tracker**
