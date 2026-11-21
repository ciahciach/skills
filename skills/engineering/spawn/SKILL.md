---
name: spawn
description: "Deleguj prace do nowej sesji worktree (spawn)."
version: 1.0.0
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

Ten skill jest jedynym źródłem prawdy o tym, **jak** oddelegować pracę do nowej sesji.
`AGENTS.md` mówi *kiedy* — ten plik mówi *czym*.

## Test: delegować czy zrobić samemu

Oddeleguj, gdy spełnione są **oba**:

- praca potrzebuje izolacji: nowy branch, osobny checkout, osobny diff, własny PR,
- da się ją opisać jednym linkiem do issue albo jednym akapitem.

Zrób sam, gdy:

- to jedno polecenie, jeden odczyt albo jedna poprawka w pliku, nad którym już siedzisz,
- zadanie dotyka tych samych plików co Twoja bieżąca praca (kolizja w tym samym checkoutcie),
- wynik jest potrzebny **teraz**, w tej turze, do podjęcia decyzji.

Zasada z metodologii Matta: **jedna sesja = jeden ticket = jeden worktree = jeden PR.**
Jeśli w normalnej pracy zrobiłbyś `stash` albo przełączył branch — to jest spawn.

## Mechanizm: narzędzie `agent_manager`

Nie ma komendy do tworzenia sesji. Jest narzędzie `agent_manager`, wywoływane z sesji.
Pierwsze użycie prosi o zgodę osobno dla `worktree`, `local` i `prompt` — to normalne.

```json
agent_manager({
  "mode": "worktree",
  "tasks": [
    {
      "name": "P03b · trwaly stan i hashe",
      "branchName": "ticket/P03b-update-state",
      "prompt": "Twoje issue: https://github.com/<org>/<repo>/issues/41. Pracuj wg AGENTS.md."
    }
  ]
})
```

Tryby:

| Tryb | Co robi | Kiedy |
|---|---|---|
| `worktree` | osobny checkout, branch, katalog, terminal | ticket, równoległy wątek, eksperyment |
| `local` | nowa sesja w bieżącym checkoutcie | druga rozmowa na tym samym branchu, bez izolacji |
| `task` (subagent) | dziecko w kontekście rodzica, wynik wraca | praca bez własnego brancha: research, analiza, czytanie |

Zarządzanie już uruchomionymi: `action: "list" | "prompt" | "stop" | "move" | "answer"`.
`action: "answer"` służy do odpowiedzi sesji, która stoi na pytaniu.

## Nazewnictwo

- `name`: `<ID> · <3–5 słów>` — ID na początku, bo `Ctrl+F` w panelu szuka po nazwie.
- `branchName`: `ticket/<ID>-<slug>` — jawnie, nigdy nie zostawiaj autogenerowania.
- Sesje dziedziczą model i reasoning z tury, w której powstały. Odpalaj spawn z sesji
  ustawionej na model, którego chcesz w pracy.

## Prompt delegowany

Trzy elementy i nic więcej:

1. link do issue (albo ścieżka do handoffu),
2. jedno zdanie zakresu, jeśli issue go nie zawiera,
3. odesłanie do `AGENTS.md`.

Zakazane w prompcie: powtarzanie treści ticketu, rytuału końcowego (push, `/pr`, STOP),
listy granic i zakazów. Wszystko to jest już w `AGENTS.md` i w treści issue. Powielone
w prompcie rozjeżdża się przy pierwszej zmianie w pliku.

## Limity

- maksymalnie **4 sesje worktree** równolegle; piąta czeka, aż któraś dojdzie do PR,
- nie odpalaj dwóch sesji na tych samych plikach — to gwarantowany konflikt,
- po spawnie **nie wykonuj tej pracy sam**: zaraportuj ID, nazwę i branch, wróć do swojego
  zadania.

## HITL zostaje

Sesja worktree ma prawo stanąć i zapytać. To nie jest błąd, który trzeba obejść, i nie
budujemy „skrzynki pytań" — człowiek chce odpowiadać na żywo. Twoim obowiązkiem jest
tylko **wychwycić** stan `waiting for input` przy `action: "list"` i powiedzieć o tym,
zamiast udawać, że sesja pracuje.

## Handoff → spawn

Gdy sesja kończy się z niedomkniętym zakresem:

1. `/handoff` pisze dokument przekazania (skill `handoff-notes`),
2. spawn nowej sesji z promptem wskazującym ten dokument:

```
agent_manager({ "mode": "worktree", "tasks": [{
  "name": "<ID> · <zakres kontynuacji>",
  "branchName": "ticket/<ID>-<slug>-c2",
  "prompt": "Kontynuuj wg handoffu: <sciezka>. Zacznij od sekcji Suggested skills."
}]})
```

Handoff trzymaj w trwałym miejscu (`%LOCALAPPDATA%\<projekt>-vault\handoffs\`), nie w `%TEMP%`
— temp jest czyszczony i dokument przekazania przestaje istnieć dokładnie wtedy, gdy jest
potrzebny.

## Wayfinder: research równolegle

Nie twórz komendy `wayfinder` — koliduje ze skillem o tej samej nazwie. Research z mapy
odpalasz z sesji, która ma wczytany skill `wayfinder`, i to ona deleguje:

```json
agent_manager({ "mode": "worktree", "tasks": [
  {"name": "D1 · research PageViews", "branchName": "wayfinder/D1-pageviews",
   "prompt": "Rozstrzygnij pytanie z mapy <url>. Notatke zapisz poza repo: <vault>\\research\\D1.md. Nie zmieniaj kodu."},
  {"name": "D2 · research LY/LQ", "branchName": "wayfinder/D2-lylq",
   "prompt": "Rozstrzygnij pytanie z mapy <url>. Notatke zapisz poza repo: <vault>\\research\\D2.md. Nie zmieniaj kodu."}
]})
```

Research nie potrzebuje PR-a: wynikiem jest notatka poza repo plus komentarz w issue.

## Kilo a Claude Code: co jest prymitywem

Metoda Matta jest przenośna na poziomie artefaktów (spec, ticket, PR, `AGENTS.md`, ADR),
ale nie na poziomie prymitywów. Poniżej różnica, żeby nie walczyć z narzędziem o funkcje,
których nie ma:

| Prymityw | Claude Code | Kilo |
|---|---|---|
| zimna sesja na żądanie | natywna, ~1 s | `Ctrl+Shift+N`; pełne tworzenie worktree ~30 s |
| spawn z poziomu agenta | narzędzie + subagenty | `agent_manager` (`worktree`/`local`/`task`) |
| spawn z poziomu skryptu | `claude -p` | CLI `kilo run` (osobna instalacja, nie w rozszerzeniu) |
| sesja jako obiekt | panel z listą i statusami | Agent Manager, ale **sekcje tylko ręczne**, brak auto-przypisania |
| scope'owanie skilli | per katalog / subagent | jedna wspólna pula; odpowiednik = `kilo agent create --permissions` |
| sygnał „needs input" | w panelu | tray tylko w aplikacji mobilnej |
| podgląd stanu z zewnątrz | — | `kilo db`, `kilo export`, `kilo stats` |

Wniosek: Kilo nie odtwarza panelu Claude Code, ale daje **lepszą obserwowalność** (SQLite
sesji, eksport transkryptu, statystyki kosztu) i równoważny spawn. Różnica, którą trzeba
zaakceptować: sekcje układasz ręcznie, więc nośnikiem cyklu życia jest nazwa i branch,
nie kolor.

## Wydajność: worktree 30 s zamiast 1 s

Samo `git worktree add` jest szybkie. Reszta to robota po utworzeniu. Zmierz po kolei:

```powershell
Measure-Command { git worktree add .kilo/worktrees/probe-1 -b probe-1 origin/main }
Get-Content .kilo/setup-script.ps1        # instalacje? kopiowanie? timeout?
```

Kolejność podejrzeń: skrypt setup (instalacje i kopiowanie `.env`), inicjalizacja snapshotu,
start LSP, indeksowanie drzewa (repo ma tysiące plików i binaria po kilka MB). Skrócenie:
pusty albo minimalny setup-script, `.kilocodeignore` na `inventory/`, `src/formulas/`,
`tests/proposals/`, `docs/*export*/`.

## Anty-wzorce

- spawn po to, żeby „mieć porządek" — pusta sesja kosztuje tyle samo co pracująca,
- spawn zadania zależnego od wyniku bieżącej pracy — poczekaj, aż będzie frontier,
- duplikowanie treści ticketu w prompcie,
- traktowanie `waiting for input` jako awarii,
- zostawianie sesji bez PR na noc — rano nie wiadomo, która jest którą.
