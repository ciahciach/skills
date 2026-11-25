# Historia sesji Kilo na Windows

Zakres: lokalny backend VS Code, w tym sidebar i Agent Manager (Local i worktree). Na Windows wykryto rozszerzenie `7.8.32`; odnośniki do kodu wskazują ten tag. Lokalnie sprawdzono tylko obecność domyślnej bazy, obecność WAL i schemat SQLite (`project`, `session`, `message`, `part`, `event`, `event_sequence`). Nie odczytano rekordów sesji, nie uruchamiano eksportu ani nie usuwano worktree. Nie zweryfikowano kompletności danych ani tego, czy każda uruchomiona instancja korzysta z tej samej bazy.

## Gdzie są dane

- Rozszerzenie uruchamia lokalny backend `serve`; katalog roboczy procesu nie wybiera bazy. Domyślny katalog danych to `xdgData/kilo`, typowo `%USERPROFILE%\.local\share\kilo` na Windows; `XDG_DATA_HOME` zmienia bazowy katalog. Zwykły plik to `kilo.db`. `KILO_DB` może wskazać inny plik albo `:memory:`, a kanały niestandardowe mogą mieć odrębny plik i fallback do dawnej nazwy. Wspólny zasięg oznacza jedną fizyczną bazę, nie wszystkie instalacje, konta, hosty VS Code/WSL czy sesje tylko w chmurze. [Start backendu][backend], [katalog XDG][global], [wybór bazy i WAL][db].
- `.kilo/agent-manager.json` to stan UI i odzyskiwania: worktree, przypisania kart sesji, zamknięte karty, sekcje i kolejność. Nie jest magazynem rozmów i nie wyznacza ich kompletnej listy. Osobno istnieje migracja starego JSON spod `storage/` w katalogu danych: m.in. `project/*.json`, `session/*/*.json`, `message/*/*.json`, `part/*/*.json`. Nie należy sumować starego i nowego magazynu w ciemno. [Agent Manager][manager], [schemat stanu UI][state], [migracja JSON][migration].
- W klasycznym schemacie rozmowy `project` → `session` → `message` → `part`. Sesja ma m.in. projekt, katalog, opcjonalnego rodzica oraz czasy utworzenia, aktualizacji i archiwizacji. `message.data` i `part.data` to JSON w kolumnach SQLite `TEXT`; relacje i czasy są w osobnych kolumnach. `event`/`event_sequence` to mechanizm synchronizacji, nie gwarantowany zapis wszystkich emisji, retry ani diagnostyki. Kod wydania definiuje też tabele nowszego formatu, np. `session_message` i `session_input`; ich lokalnej obecności i pokrycia nie ustalano. [Schemat SQL][sql], [synchronizacja][sync].

## Co zachowuje historia

| Typ | Co zapisuje backend i czego nie gwarantuje |
| --- | --- |
| Prompt i odpowiedź | Wiadomości `user` i `assistant` oraz ich części, m.in. `text` i `file`. To zapis rozmowy, nie kopia kompletnego requestu do modelu ani każdego komunikatu systemowego; istnieją części syntetyczne. |
| Reasoning | `part.type = reasoning` z tekstem/metadanymi, jeśli dostawca udostępni je w strumieniu, a backend zapisze. Statystyka tokenów reasoning nie oznacza, że tekst jest dostępny. |
| Narzędzia i MCP | `part.type = tool` ze stanami `pending`, `running`, `completed`, `error`; zależnie od stanu m.in. wejście, wynik, błąd i metadane. MCP trafia do tego samego mechanizmu; wynik jest przetwarzany, może zostać obcięty, a nieobsługiwana treść pominięta. Nie jest to log całego protokołu MCP. |
| Błędy | Błąd wykonania narzędzia może znaleźć się w `state.error`, a błąd generacji w opcjonalnym polu `assistant.error`. Publikacja `Session.Event.Error`, np. przy odrzuceniu promptu, sama nie dowodzi istnienia rekordu rozmowy. Nie utożsamiać historii z logami procesu, transportu ani rozszerzenia. |

Źródła: [typy rozmowy][types], [zapis i błędy promptu][prompt], [procesor rozmowy][processor], [transformacja MCP][tools]. To możliwości schematu i kodu, nie obserwacja zawartości lokalnych sesji.

## Zasięg i usunięcie worktree

- Agent Manager rozdziela historię na projekty i konteksty Local/Worktree. Backend ma globalną listę w obrębie bazy i opcjonalne ograniczenia do katalogu lub rodziny worktree. `kilo session list --all` pokazuje sesje główne, nie dzieci, i domyślnie pomija zarchiwizowane. Lokalny recall przeszukuje rodzinę projektu i wybiera typy części (m.in. tekst, pliki, błędy narzędzi), a nie komplet zdarzeń ze wszystkich projektów. [Historia w Agent Managerze][manager], [CLI list][list], [globalne filtry][filters], [recall][recall].
- Zwykłe usunięcie checkoutu zarządzanego przez Agent Manager to nie usunięcie rozmowy. Ścieżka usunięcia sprawdza aktywność i zbiera także sesje potomne i zarchiwizowane, usuwa checkout, próbuje przenieść zachowane sesje do katalogu głównego projektu i usuwa wpis UI. Nieudane przeniesienie może pogorszyć odnajdywanie sesji, ale nie kasuje rozmowy. Po zewnętrznym zniknięciu katalogu sprzątanie osieroconego wpisu operuje na stanie UI; nie jest gwarancją prawidłowej trasy do sesji ani zachowania oryginalnego przypisania worktree. Osobne ścieżki to jawne usunięcie sesji oraz rollback nieudanego setupu, który może wywołać `session.delete`. Checkpointy są sprzątane osobno. Wnioski wyłącznie z kodu. [Cykl życia worktree][lifecycle], [rollback setupu][discard], [kaskady SQL][sql].

## Eksport, odczyt i okno dat

- `kilo export [sessionID]` wypisuje JSON jednej sesji (`info` i `messages` z częściami). `--sanitize` redaguje wybrane pola, ale pozostawia m.in. identyfikatory i może pozostawiać treści błędów; nie gwarantuje anonimizacji. CLI `session list` również ujawnia metadane wrażliwe i nie ma filtra dat. Żadnego z tych poleceń nie uruchamiano na realnych danych. [Eksport][export], [CLI list][list].
- Lokalny `GET /experimental/session` obsługuje `start` (`time_updated >= start`), `cursor` (`time_updated < cursor`) i `archived=true` (uwzględnia archiwum). To milisekundy Unix i kryterium aktualizacji **sesji**, nie czasu powstania zdarzenia. Kursor ma tylko czas, mimo wtórnego sortowania po ID, więc przy remisie na granicy może pominąć wiersze. [API][api], [handler][handler], [filtry][filters], [znaczniki czasu][time].
- Dla backfillu wiadomości od 16.11.2026: określić strefę początku dnia, przeliczyć na Unix ms i użyć półotwartego okna `[od, do)` na `message.time_created`. Dla osobno analizowanych aktualizacji części świadomie wybrać `part.time_created` albo `part.time_updated`; to nie odtworzy oryginalnych zdarzeń strumienia. Wariant bez utraty rekordów na remisach wymaga stabilnego klucza porządku, np. `(czas, id)`, wewnętrznie. To propozycja semantyki, nie potwierdzenie dostępności danych od wskazanej daty. [Schemat][sql], [znaczniki czasu][time].
- Bezpośredni SQL to lokalna ścieżka do schematu i kontroli projekcji, ale schemat jest zależny od wydania. Do tej inspekcji użyto połączenia `mode=ro&immutable=1` wyłącznie dla schematu. Lokalna baza ma sidecar WAL, więc tej techniki nie należy używać jako spójnego widoku żywej historii: może nie obejmować zmian w WAL, a `immutable` zakłada niezmienność pliku. Do przyszłego backfillu wymagać spójnego odczytu uwzględniającego WAL lub autoryzowanego spójnego snapshotu, bez uruchamiania migracji na źródle. Snapshot lub pełny eksport sam w sobie zawiera dane wrażliwe. [Inicjalizacja bazy][db], [SQLite WAL][wal], [SQLite URI][uri].

[manager]: https://kilo.ai/docs/automate/agent-manager#sessions-and-history
[backend]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/kilo-vscode/src/services/cli-backend/server-manager.ts
[global]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/core/src/global.ts
[db]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/storage/db.ts
[state]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/kilo-vscode/src/agent-manager/WorktreeStateManager.ts
[migration]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/kilocode/storage/json-migration.ts
[sql]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/core/src/session/sql.ts
[sync]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/sync/index.ts
[types]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/schema/src/v1/session.ts
[prompt]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/session/prompt.ts
[processor]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/session/processor.ts
[tools]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/session/tools.ts
[list]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/cli/cmd/session.ts
[filters]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/kilocode/session/index.ts
[recall]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/kilocode/session/recall-search.ts
[lifecycle]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/kilo-vscode/src/agent-manager/provider-lifecycle.ts
[discard]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/kilo-vscode/src/agent-manager/discard-worktree.ts
[export]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/cli/cmd/export.ts
[api]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/server/routes/instance/httpapi/groups/experimental.ts
[handler]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/server/routes/instance/httpapi/handlers/experimental.ts
[time]: https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/core/src/database/schema.sql.ts
[wal]: https://sqlite.org/wal.html#read_only_databases
[uri]: https://sqlite.org/uri.html#recognized_query_parameters
