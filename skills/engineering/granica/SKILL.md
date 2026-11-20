---
name: granica
description: Use when: compact, clear, handoff or continue?
disable-model-invocation: true
---

# Granica

Podejmij decyzję o **granicy fazy**: kontynuować w tej sesji, `/clear`, `/handoff`, subagent czy
`/compact`. Wynik to jedna rekomendacja, jedno zdanie uzasadnienia i jedno polecenie do wpisania.
Nie prowadź wywiadu i nie opisuj drzewa — użytkownik chce rozstrzygnięcia, nie lektury.

Drzewo jest w [ask-matt/PHASE-BOUNDARIES.md](../ask-matt/PHASE-BOUNDARIES.md). Czytaj je w podanej
kolejności; pierwsze „tak" wygrywa.

## Nie licz tokenów

Nie widzisz swojego zużycia i harness zwykle nie wstawia go do rozmowy. **Nie zgaduj liczby** i nie
pytaj o nią. Jeśli użytkownik podał ją sam (np. `/granica 120k`), użyj jej jako jednego z sygnałów,
nigdy jako progu, który sam rozstrzyga.

## Najpierw ustal, czy w ogóle jest granica

Nazwij fazy tej sesji — jedna linia każda (np. „wywiad", „implementacja zielonego", „review") — i
powiedz, czy ostatni krok się **domknął**:

- **domknięty** — test przechodzi, ticket rozwiązany, diff gotowy, pytanie rozstrzygnięte → jest
  granica, przechodź do pytań,
- **niedomknięty** — w połowie red-green, w połowie pliku, czekasz na wynik narzędzia → **nie ma
  decyzji**: Continue albo podziel resztę na subagenta. Compakt w środku fazy gubi wątek.

## Pięć pytań, w tej kolejności

1. **Czy następna faza potrzebuje tej sesji jako źródła pierwotnego?** Wywiad → implementacja,
   implementacja → review tego samego diffu: tak. Wtedy **Continue** — i to jest najczęstsza
   poprawna odpowiedź, bo Continue nic nie kosztuje i nic nie traci.
2. **Czy to, co tu jest, jest zbędne dla tego, co dalej?** Eksploracja, ślepe zaułki, wczytane pliki,
   których już nie użyjesz → **`/clear`**. Najtańszy ruch; stara sesja zostaje wznawialna.
3. **Czy praca podróżuje?** Nowy harness, inny katalog albo repo, inny człowiek, albo side-task
   odpalany w trakcie → **`/handoff`**. Jeśli nic nie podróżuje, handoff jest zbędny.
4. **Czy da się to zrobić AFK?** Wąsko zakrojone, bez sterowania — review diffu, research, regresja →
   **subagent**; ta sesja zostaje nietknięta.
5. W przeciwnym razie **`/compact`** z instrukcją, co ma przetrwać:
   `/compact idziemy do review tego diffu`.

## Odpowiedź

Trzy linie, bez rozprawki:

- **Gdzie jesteś:** fazy i czy ostatni krok się domknął.
- **Decyzja:** jedno z pięciu plus odwołanie do numeru pytania, które ją wybrało.
- **Co wpisać:** dokładne polecenie gotowe do wklejenia. Przy handoffie od razu pięć linii: co
  zrobione, co zostało, gdzie leży plan, następny krok, czego nie ruszać.

Gdy dwie opcje są równie dobre, wybierz tę, która **mniej traci**: Continue przed `/compact`,
`/clear` przed `/handoff`. Gdy użytkownik wybierze inaczej — to jego sesja; zaznacz koszt w jednym
zdaniu i nie wracaj do tematu.
