---
name: retrofit-repo
description: Doprowadź istniejące repo do standardów setupu — audyt, plan, bilety.
---

# Retrofit repo

Repo ma historię: milestone'y, własny rejestr decyzji, backlog w wiki, `AGENTS.md` pisany ręcznie.
Ten skill **nie migruje** — robi audyt, plan i bilety, po jednym na partię, żeby każda partia
zmieściła się w jednym oknie kontekstu.

> **When to use:** repo pracuje dłużej niż tydzień i nie było w nim `/setup-matt-pocock-skills`,
> albo setup był, ale standardy się rozjechały.

## Czego ten skill nie robi

- **Nie przenosi treści.** żadnego `git mv`, żadnych zmian nazw, żadnego usuwania.
- **Nie tnie biletów ze specu.** Od tego jest `/to-spec` i `/to-tickets`.
- **Nie wykonuje partii.** Bilety wykonuje `/implement`, każdy w osobnej sesji.

Jeśli audit wykaże, że repo jest już zgodne, odpowiedź brzmi „nic do zrobienia” — i to jest wynik.

Drugie uruchomienie na tym samym repo **nie tworzy drugiego zestawu biletów**: jeśli
`.scratch/retrofit/issues/` już istnieje, przeczytaj istniejące bilety, uzupełnij tylko brakujące
partie i w raporcie napisz, co doszło. Duplikat biletu kosztuje więcej niż jego brak.

## 1. Preflight

```bash
git status --short          # brudne drzewo = STOP, migracja na niezacommitowanych zmianach jest nieodwracalna
git log --oneline -5
git remote -v
git ls-files -z | xargs -0 du -h 2>/dev/null | sort -rh | head -10   # co waży najwięcej
```

Jeśli drzewo jest brudne, powiedz to i zaproponuj commit albo `git stash`, zanim cokolwiek napiszesz.
Nie decyduj za użytkownika, że „te zmiany są nieistotne”.

## 2. Audyt — tabela rozjazdów

Sprawdź każdy punkt i zapisz werdykt. Nie naprawiaj w trakcie: to jest lista, nie zadanie.

| Obszar | Co sprawdzić | Werdykt |
|---|---|---|
| konfiguracja | `docs/agents/{issue-tracker,triage-labels,domain}.md` | brak → partia 01 |
| instrukcje | `AGENTS.md` / `CLAUDE.md`, bloki `## Agent skills`, `## Wiki` | brak lub zduplikowane → partia 01 |
| wiki | `wiki/index.md`, `wiki/decisions/` + rejestr jedno-plikowy, `wiki/processes/grill/` | brak indeksu → partia 02 |
| decyzje | czy istnieje rejestr jedno-plikowy; czy są ADR-y poza nim | duplikat → partia 02 |
| etapy | czy istnieją milestone'y; które są zamknięte, które otwarte | zamknięte → partia 03 |
| kolejki | ile miejsc udaje kolejkę: `.scratch/`, backlog w wiki, tracker zewnętrzny | więcej niż jedno → partia 04 |
| otwarta praca | pozycje „do zrobienia” w etapach i backlogach | → partia 05 |
| słownik | `GLOSSARY.md` | brak przy niepustej domenie → partia 02 |
| higiena | duże binaria w gicie, sekrety w plikach, `.gitignore` | raport, bez zmian |

Weryfikacja faktów należy do Ciebie: przeczytaj pliki, nie zgaduj z nazw.

## 3. Plan i bilety

Zapisz plan w `.scratch/retrofit/plan.md`: tabela z audytu plus decyzje, których nie umiesz podjąć
sam. Potem wytnij bilety do `.scratch/retrofit/issues/NN-<slug>.md` — po jednym na partię.

Domyślny podział, z budżetem na partię:

| NN | Partia | Budżet | Blokady |
|---|---|---|---|
| 01 | `docs/agents/*` + bloki w instrukcjach | ≤ 45k | — |
| 02 | indeks decyzji + pierwszy ADR + `GLOSSARY.md` | ≤ 40k | 01 |
| 03 | zamrożenie zamkniętych etapów (nagłówek „zapis historyczny”) | ≤ 25k | 01 |
| 04 | wybór jednej kolejki (reszta zamrożona wskaźnikiem) | ≤ 30k | 03 |
| 05 | otwarta praca → bilety `needs-triage`, po jednym na pozycję | ≤ 60k | 04 |
| 06 | weryfikacja i raport końcowy | ≤ 30k | 02–05 |

Budżety są sufitami, nie celami. Partia, która ich nie mieści, dzieli się na dwie — to jest jedyne
dozwolone „przekroczenie” planu.

Szablon biletu:

```markdown
# <NN>: <nazwa partii>

**Budget:** ≤ <N>k tokenów. Po 75% budżetu bez końca: zapisz handoff i stop.
**Blocked by:** <numery albo „None (can start immediately)”>
**Status:** needs-triage

- [ ] <kryterium akceptacji 1>
- [ ] <kryterium akceptacji 2>

## Handoff
<uzupełnia wykonawca: co zrobione, co zostało, następny krok>
```

`Status: needs-triage`, nie `ready-for-agent`: to użytkownik decyduje, co wchodzi w tej kolejności.

## 4. Budżet kontekstu

Ten skill sam podlega limitowi: audyt zamknij w ~60k. Jeśli audit się nie mieści, podziel go na dwa
przebiegi (konfiguracja i instrukcje, potem wiki i kolejki) i zapisz wynik pierwszego w `plan.md`,
żeby drugi nie zaczynał od zera.

| Zużycie | Decyzja |
|---|---|
| do ~80k | audyt albo planowanie bez ograniczeń |
| 80–120k | dokończ bieżącą fazę, potem zamknij |
| 120–150k | nie zaczynaj fazy: handoff i stop |
| > 150k | tylko handoff w pięciu liniach |

## 5. Raport

Pięć linii i tabela: co jest zgodne, co rozjechane, ile biletów powstało, czego **nie** ruszyłeś
i dlaczego. Bez tego raportu użytkownik nie wie, czy oddać repo agentowi na partię 01.

<!-- next-step-pointer -->
> **Before you finish:** name the next step with the `co-dalej` skill (it reads the repo state
> and picks one), or state it yourself in one line with the exact command.
