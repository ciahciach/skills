---
name: co-dalej
description: Wskaż jeden następny krok na podstawie stanu Issue, zmian w Git lub odbioru skoroszytu.
disable-model-invocation: true
---

# Co dalej

Uruchom tę procedurę wyłącznie na jawne wywołanie użytkownika (`/co-dalej` lub prośba o użycie skilla z nazwy). Samo załadowanie instrukcji, odsyłacz z innego skilla ani zakończenie etapu nie są wywołaniem. Tylko odczyt i rekomendacja: nie wykonuj kroku, nie wywołuj rekomendowanego skilla i nie zmieniaj stanu repo, Issue trackera, sesji ani skoroszytu.

## Ustal zakres i stan

1. Zacznij od wskazanego Issue, PR-a, grafu albo skoroszytu. Bez odsyłacza użyj bieżącego zlecenia i potwierdź powiązanie z checkoutem lub sesją. Nazwa brancha czy sam plik to trop, nie dowód. Jeśli po odczycie zostaje kilka równie prawdopodobnych celów, poproś o jeden identyfikator zamiast wybierać za użytkownika. Nie dobieraj pracy spoza zakresu.
2. Przeczytaj aktualny `GLOSSARY.md` (jeśli istnieje) oraz właściwe wskazówki z `AGENTS.md`, `CLAUDE.md` i `docs/agents/domain.md`. Odszukaj skonfigurowany Issue tracker i mapowanie ról triage. W trybie wiki podążaj za wskazanymi ledgerami i ADR-ami. Brak pliku konwencji nie oznacza braku konfiguracji: użyj kanonicznego odsyłacza z instrukcji repo lub od użytkownika.
3. Odczytaj tylko dowody potrzebne do danego kroku: treść i kryteria Issue, jego rolę triage, zależności i aktualne decyzje; stan checkoutu i diff; w PR sprawdź bazę, aktualny SHA, zakres, review, wymagane testy i ewentualny merge. W Kilo VS Code, jeśli to istotne, sprawdź stan właściwej sesji w Agent Managerze. W Excelu czytaj instrukcje repo, aktualny eksport i raporty; nie otwieraj skoroszytu. Wskaż `niezweryfikowane`, jeśli źródła nie są dostępne albo sobie przeczą. Zamknięte Issue może oznaczać przekazanie zakresu, nie wykonanie lub odbiór; sprawdź dowód i Issue, które przejęło resztę.

## Wybierz jeden krok

Wybierz najbliższy niespełniony warunek dla tego zakresu. Jeśli brak dowodu rozstrzyga o gotowości, następnym krokiem jest sprawdzenie konkretnego dowodu, nie implementacja na podstawie założenia.

- **HITL lub blokada.** Wskaż dokładną decyzję, czynność lub zgodę i jej właściciela. W Kilo rozróżnij odpowiedź na natywne pytanie od zatwierdzenia permission. Przy niepewnym starcie albo przekazaniu zapisu wskaż uzgodnienie faktycznego stanu, nie kolejny start. Blokada zatrzymuje zależny zakres, nie niezależne Issue w zleconym grafie.
- **Triage role.** Stosuj mapowanie repo: `needs-triage` kieruje do `/triage`, `needs-info` do uzyskania konkretnej informacji, `ready-for-human` do wskazanego człowieka, a `wontfix` kończy zakres bez wdrażania. `ready-for-afk` (np. `ready-for-agent`) nie zastępuje dowodu spełnienia zależności ani zgody wymaganej przez kryteria.
- **Issue i planowanie.** Surowe zgłoszenie kieruj do `/triage`; nierozstrzygnięty pomysł do `/grill-with-docs`, a duży niejasny zakres do `/wayfinder`. Uzgodniony zakres wielosesyjny bez specyfikacji kieruj do `/to-spec`, a przyjętą specyfikację bez podziału do `/to-tickets`. Gotowe pojedyncze Issue z jasnymi kryteriami, spełnionymi zależnościami i bez aktywnego wykonawcy kieruj wprost do `/implement`, bez wymagania ledgera czy osobnej specyfikacji. `/implement-spec` rekomenduj dla wskazanego grafu, nie całego Issue trackera. W Kilo zależny wykonawca czeka na potwierdzony merge wymaganej zmiany do właściwej bazy, nie na sam zielony CI, gotowy PR ani zamknięcie Issue.
- **Zmiana i PR.** Niekompletny zakres, także w częściowym PR-ze, kieruj do dokończenia brakującego kryterium albo do jawnego wydzielenia uzgodnionej reszty. PR pokrywający jedynie podzakres nie dowodzi ukończenia całego Issue. Po implementacji wskaż brakującą weryfikację lub `/code-review` aktualnego diffu; po wymaganych testach i aktualnym review wskaż commit, publikację PR-a lub merge, zależnie od faktycznego etapu. W Kilo merge jest krokiem człowieka; nie jest zgodą na wydanie ani wdrożenie.
- **Excel.** Jeśli celem jest utworzenie lub adopcja scaffolda, wskaż `/setup-excel-repo` niezależnie od obecności skoroszytu. Do review aktualnego eksportu użyj tekstu. Przy zmianie skoroszytu kieruj przez udokumentowane wejście `excel-router` i kontrakt repo; nie wybieraj backendu w zastępstwie routera. Jeśli do rutynowej operacji brakuje zgody, kwalifikacji dla profilu/operacji albo kontroli backendu, wskaż brak jako warunek. Po merge kodu ustal uprawnione uruchomienie integracji, przypięty SHA kodu i bazę z checksumą. Rozróżnij plan bez zapisu, zapis na odrębnej kopii, niezależne reopen/re-export, wymagane testy funkcjonalne oraz jawny odbiór konkretnej zweryfikowanej kopii przez właściciela. Import M nie jest odświeżeniem ani dowodem wykonania M. Zależna zmiana struktury wymagająca wyłączności rusza dopiero na aktualnej przyjętej bazie i po osobnym uzyskaniu wyłączności zapisu.
- **Koniec zakresu.** Jeśli wszystkie wymagane kryteria mają dowody, podaj, że nie ma kolejnego kroku w tym zakresie. Nie dorabiaj retro, odbioru, publikacji ani sprzątania bez podstawy w zleceniu.

## Odpowiedź

**Stan:** nazwij zakres i podaj najkrótszy rozstrzygający dowód (link, SHA, raport albo brakujący fakt).

**Następny krok:** jedna komenda dostępna na danym hoście lub jedna konkretna czynność, z nazwanym właścicielem jeśli wymaga HITL. Bez listy alternatyw i bez pytania o zgodę na wykonanie. Jeśli zakres jest niejednoznaczny, jedynym krokiem jest wskazanie brakującego identyfikatora.

## Przykłady

Poniższe identyfikatory są przykładowe.

| Dowód | Jeden następny krok |
|---|---|
| Issue #12 ma jasne kryteria i brak niespełnionych zależności; nie ma przypisanego wykonawcy ani powiązanego PR-a. | `/implement #12` |
| Sesja A czeka na natywne pytanie o wybór wariantu. | **HITL:** użytkownik wybiera wariant w pytaniu sesji A. |
| PR #24 po merge dodał eksport formuł, ale Issue obejmuje też kontrolowany import. | Dokończyć kontrolowany import w osobnym PR-ze powiązanym z Issue. |
| Oba PR-y z M scalone; jest przypięta baza, ale brak autoryzacji wykonania integracji. | **HITL:** uprawniona osoba zatwierdza integrację wskazanego SHA na odrębnej kopii tej bazy. |
| Kopia zapisana, bez niezależnego reopen/re-export. | Zweryfikować zapisaną kopię zgodnie z kontraktem repo. |
| Raport potwierdza obie zmiany M i niezmienione miejsca ładowania; brak odbioru. | **HITL:** właściciel przyjmuje kopię z SHA-256 wskazanym w raporcie. |
