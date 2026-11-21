---
name: spawn
description: "Deleguj prace do nowej sesji worktree (spawn)."
version: 1.3.0
author: "ciahciach"
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, worktree, sessions, parallel]
    created_by: agent
---

> **Kiedy używać:** gdy praca wymaga własnego brancha, checkoutu albo diffu, a Ty masz ją
> oddelegować, a nie wykonać. Także wtedy, gdy wracasz do zadania po handoffie.

# Spawn

Jedyne źródło prawdy o tym, **jak** oddelegować pracę. `AGENTS.md` mówi *kiedy*.

## Wywołanie

`/spawn <payload>` — argument to **reszta wiadomości** po nazwie skilla. Nie ma tu
`$ARGUMENTS` ani szablonu (to mechanizm plików komend, nie skilli): skill dostaje tekst
jako kontekst i sam z niego buduje nazwę, branch i prompt.

```
/spawn /wayfinder ułóż mapę skilli w repo ciahciach/skills
/spawn /implement https://github.com/<org>/<repo>/issues/43
```

Nazwę i branch wyprowadź z payloadu: token bez wiodącego `/` wersalikami + ` · ` + 3–5 słów
reszty (`WAYFINDER · ułoż mapę skilli`, branch `wayfinder/uloz-mape-skillow`).

W spawnowanej sesji **nie licz na to, że wiodący `/` w prompcie zostanie sparsowany jako
komenda**. Tool przekazuje prompt jako wiadomość, nie przez parser slashy. Pisz słownie:

```
Użyj skilla wayfinder. <reszta argumentu>
```


## Test: delegować czy zrobić samemu

Oddeleguj, gdy spełnione są **oba**: praca potrzebuje izolacji (branch, checkout, diff, PR)
i da się ją opisać jednym linkiem do issue albo jednym akapitem.

Zrób sam, gdy: to jedno polecenie lub odczyt, zadanie dotyka plików, nad którymi siedzisz,
albo wynik jest potrzebny w tej turze do decyzji.

Reguła Matta: **jedna sesja = jeden ticket = jeden worktree = jeden PR.** Jeśli w normalnej
pracy zrobiłbyś `stash` albo przełączył branch — to jest spawn.

## Mechanizm: narzędzie `agent_manager`

Dostępne **tylko w rozszerzeniu VS Code** (Agent Manager to funkcja rozszerzenia, nie CLI —
CLI ma własne odpowiedniki, patrz niżej). Pierwsze użycie prosi o zgodę, osobno dla każdej
zdolności.

```json
agent_manager({
  "mode": "worktree",
  "versions": false,
  "tasks": [{
    "name": "P03b · trwaly stan i hashe",
    "branchName": "ticket/P03b-update-state",
    "prompt": "Twoje issue: https://github.com/<org>/<repo>/issues/41. Pracuj wg AGENTS.md."
  }]
})
```

Tryby: `worktree` (nowy checkout, branch, katalog, terminal), `local` (sesja w bieżącym
checkoutcie; można wskazać istniejący worktree przez `worktreeID`), `task` (subagent —
**nie tworzy worktree**, wynik wraca do rodzica).

### Co naprawdę przyjmuje `tasks[]`

| Pole | Status |
|---|---|
| `name`, `branchName`, `prompt` | działają |
| `model`, `provider`, `variant` | działają — model i reasoning per zadanie |
| `agent`, `mode` | **nie działają** — zgłoszone w Kilo-Org/kilocode#13827, status `discussion` |

Sesja z promptem dziedziczy model i reasoning z bieżącej tury, chyba że podasz inny.
Przed podmianą modelu sprawdź dostępne: narzędzie `agent_manager_models`.

Skoro `agent`/`mode` nie przechodzą przez narzędzie, dwie drogi:

- **ręcznie**: okno New Worktree obsługuje `/models`, `/agents`, `/variant`, `/sandbox` —
  `/agents` wybiera tryb/agenta jeszcze przed startem,
- **z CLI**: `kilo run --agent <nazwa>` albo `kilo worktree create`.

Nie obchodź tego wstrzykiwaniem persony do promptu: zjada kontekst, kłóci się z instrukcjami
bazowego agenta i nie daje scope'owania narzędzi.

## Uprawnienia: każda zdolność osobno

Zgoda jest rozdzielona per zdolność. Zatwierdzenie `worktree` **nie** zatwierdza `local`,
przeglądu (`list`), promptu do istniejącej sesji, stopu, przeniesienia ani odpowiedzi.
Prompt do istniejącej sesji wymaga własnej zgody `prompt`, nawet gdy tworzenie sesji
zatwierdzono wcześniej zbiorczo.

Odpowiedź na pytanie musi użyć **dokładnych etykiet opcji** z pytania. Zatwierdzenie planu
może uruchomić implementację — czytaj, co zatwierdzasz.

## Stany, kolejka i HITL

- prompt do sesji zajętej albo w `retrying` trafia do kolejki; narzędzie wraca po przyjęciu,
  nie po zakończeniu pracy,
- sesja z **oczekującym pytaniem albo prośbą o uprawnienie odrzuca prompt** — najpierw
  `action: "answer"` albo rozstrzygnięcie uprawnienia w panelu,
- `action: "stop"` przerywa pracę i usuwa sesję z panelu, jak zamknięcie karty,
- HITL zostaje i jest pożądany. Nie buduj „skrzynki pytań". Twoim obowiązkiem jest wyłapać
  `waiting for input` przez `action: "list"` i powiedzieć o tym, nie udawać, że sesja pracuje.

## Sekcje

Wbrew temu, co sugeruje UI: **sekcje da się ustawiać programowo**. `action: "move"`
przyjmuje ID sekcji z przeglądu albo `null`, żeby wyjąć z grupy. Przeniesienie sesji przenosi
cały worktree razem z braćmi z trybu multi-version. **Sesji `local` nie da się przypisać do
sekcji.**

## Nazewnictwo i limity

- `name`: `<ID> · <3–5 słów>`, ID na początku — `Ctrl+F` szuka po nazwie,
- `branchName`: `ticket/<ID>-<slug>`, jawnie. Automatyczne nazywanie branchy jest domyślnie
  włączone i nie zmienia nazw podanych wprost ani opublikowanych,
- **20 zadań** na jedno żądanie, ale trzymaj **4 sesje worktree** — wąskim gardłem jest
  Twoje review,
- `versions: true` uruchamia do **4 równoległych wariantów** tego samego promptu (porównanie
  podejść, nie zwiększanie przepustowości),
- nie odpalaj dwóch sesji na tych samych plikach w jednym worktree — dzielą checkout, branch
  i terminal.

## Cykl życia worktree

- worktree powstają w `.kilo/worktrees/`, stan panelu w `.kilo/agent-manager.json`,
- **zamknięcie zarządzanego worktree usuwa katalog i lokalny branch** — pushuj przed
  `Ctrl+Shift+W`,
- nowe worktree twórz z **głównego repo**, nie z istniejącego checkoutu worktree,
- `/update-from-base` zachowuje staged/unstaged/untracked w zweryfikowanej kopii odzyskania,
  robi merge świeżej bazy i odtwarza zmiany; **nie używa `git stash`** i przerywa, gdy
  konflikt wymaga decyzji. Przy „Push Pull Request Fixes" pushuje po czystym merge.

## Setup i run script

`.kilo/setup-script.ps1` (Windows; `setup-script`, `.sh`, `.cmd`, `.bat`) uruchamia się przy
każdym nowym worktree, z `WORKTREE_PATH` i `REPO_PATH`, w **limicie 5 minut**. Kilo samo
kopiuje tylko korzeniowe `.env` i `.env.*` — nic zagnieżdżonego, żadnych nadpisań.
`.kilo/run-script.ps1` uruchamiasz `Ctrl+E` w wybranym worktree, z tymi samymi zmiennymi.

## Wydajność: skąd 30 s na worktree

Zmierzone w repo Versuni (1980 plików, binaria po 2–11 MB):

| Etap | Czas |
|---|---|
| `git worktree add` (checkout 1980 plików) | **5,8 s** |
| `git status --porcelain` | 0,7 s |
| setup script | **brak pliku** — nie jest przyczyną |
| reszta (~24 s) | inicjalizacja Kilo: snapshot, LSP, indeksowanie, boot sesji |

Kolejność działania:

1. **Zmierz drugie worktree pod rząd.** Jeśli jest wyraźnie szybsze, te 24 s to cold start
   runtime'u, a nie koszt per worktree — wtedy nie ma czego optymalizować, trzeba tylko nie
   zamykać panelu.
2. **Wyklucz repo z real-time scan Defendera** — na Windows to zwykle największy zysk,
   bo skanowany jest każdy z 1980 plików zapisanych przy checkoutcie.
3. **Sparse checkout dla ticketów, które nie potrzebują binariów**:
   `git worktree add --no-checkout <dir> -b <branch>` + `git sparse-checkout set tests tools wiki docs`.
   Checkout spada z 1980 plików do setek.
4. `.kilocodeignore` na `inventory/`, `src/formulas/`, `tests/proposals/`, `docs/*export*/`
   — mniej plików do indeksowania.
5. `git config feature.manyFiles true` — szybszy `git status` na dużych drzewach.

Realnie 30 s → 8–10 s jest osiągalne. Parytetu 1 s nie będzie: u Matta nie ma snapshotu,
LSP ani indeksowania na starcie.

## Prompt delegowany

Trzy elementy: link do issue (albo ścieżka handoffu), jedno zdanie zakresu, odesłanie do
`AGENTS.md`. Zakazane w prompcie: treść ticketu, rytuał końcowy (push, `/pr`, STOP), listy
granic. Wszystko to jest już w `AGENTS.md` i w issue — powielone rozjeżdża się przy pierwszej
zmianie pliku.

## Po decyzji: tickety i spawn frontieru

Decyzja człowieka jest **wejściem**, nie wyjściem. Gdy ją dostaniesz:

1. Zapisz C3 — komentarz z linkiem do wypowiedzi człowieka i wybranym wariantem.
2. Jeśli decyzja zmienia kontrakt, zapisz nowy ADR (nowy plik; nie edytuj istniejącego).
3. Rozbij zakres na tickety. Każde dziecko z własnym „Dowodem PASS" i granicami.
   Rodzic zostaje ticketem śledzącym, bez etykiety `ready-for-agent`.
4. Ustaw blokady **natywnie** (`--blocked-by`, `--parent`), nigdy w prozie.
5. Spawnuj **wyłącznie frontier** — tickety z zerem otwartych blokerów. Spawn zależnego
   ticketu to robota na wyrok: agent nie zna wyniku poprzednika i wymyśli go.
6. Zakończ turę raportem: co utworzone, co odpalone, co czeka na czyj wynik.

Frontier sprawdzasz zawsze tym samym zapytaniem:

```bash
gh api "repos/$R/issues?state=open&per_page=100" --paginate --jq '
  [.[]|select(.pull_request==null)]|.[]|
  select((.issue_dependencies_summary.blocked_by//0)==0)
  |select([.labels[].name]|index("ready-for-agent"))
  |"#\(.number)\t\(.title)"'
```

Taka sama kolejność jest u Matta: `to-tickets` tnie spec na graf z blokadami, a
`implement-spec` bierze z tego grafu **frontier** i uruchamia po jednym subagencie na
ticket. Różnica, którą trzeba świadomie zaakceptować: on tnie spec osobnym krokiem,
Ty możesz ciąć bezpośrednio z decyzji — pod warunkiem, że blokady są natywne.

## Handoff → spawn

`/handoff` pisze dokument przekazania, potem spawn nowej sesji z promptem wskazującym ten
dokument. Handoff trzymaj w trwałym miejscu (`%LOCALAPPDATA%\<projekt>-vault\handoffs\`),
nie w `%TEMP%` — temp jest czyszczony dokładnie wtedy, gdy dokument jest potrzebny.

## Wayfinder: research równolegle

Nie twórz komendy `wayfinder` — koliduje ze skillem o tej samej nazwie. Deleguje sesja,
która ma wczytany skill `wayfinder`, trybem `worktree` z branchem `wayfinder/<ID>-…`.
Wynikiem researchu jest notatka poza repo plus komentarz w issue, nie PR.

## Kilo a Claude Code: co jest prymitywem

Metoda Matta jest przenośna na poziomie artefaktów (spec, ticket, PR, `AGENTS.md`, ADR), ale
nie na poziomie prymitywów.

| Prymityw | Claude Code | Kilo |
|---|---|---|
| spawn z poziomu agenta | narzędzie + subagenty | `agent_manager` (`worktree`/`local`) oraz `task` |
| wiązanie roli z sesją | agent per subagent | **brak w narzędziu**; UI `/agents` albo CLI `--agent` |
| spawn ze skryptu | `claude -p` | `kilo run` (osobna instalacja, nie w rozszerzeniu) |
| sesja jako obiekt | panel z listami i statusami | Agent Manager; sekcje **da się** ustawiać przez `move` |
| scope'owanie skilli | per katalog / agent | wspólna pula; odpowiednik = `kilo agent create --permissions` |
| sygnał „needs input" | w panelu | tray w aplikacji mobilnej; w VS Code przez `list` |
| obserwowalność z zewnątrz | — | `kilo db`, `kilo export`, `kilo stats` |

Kilo nie odtwarza panelu Claude Code, ale daje lepszą obserwowalność (SQLite sesji, eksport
transkryptu, statystyki kosztu) i równoważny spawn. Różnica do zaakceptowania: nośnikiem
cyklu życia jest nazwa i branch, nie kolor sekcji.

## Anty-wzorce

- spawn po to, żeby „mieć porządek" — pusta sesja kosztuje tyle samo co pracująca,
- spawn zadania zależnego od wyniku bieżącej pracy — poczekaj, aż będzie frontier,
- wstrzykiwanie persony do promptu zamiast `/agents` albo `--agent`,
- prompt do sesji, która stoi na pytaniu (zostanie odrzucony),
- traktowanie `waiting for input` jako awarii,
- zamykanie worktree przed pushem (ginie lokalny branch),
- zostawianie sesji bez PR na noc — rano nie wiadomo, która jest którą.
