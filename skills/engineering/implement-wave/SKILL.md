---
name: implement-wave
description: Zrób falę niezależnych biletów równoległymi subagentami, potem scal.
---

# Implement wave

Wykonaj **kilka biletów naraz** przez równoległe subagenty (`task` z `background: true`) w jednym
checkoucie, a potem zweryfikuj i zacommituj wynik po bilecie.

> **When to use:** frontier ma co najmniej dwa bilety, żaden nie blokuje drugiego, a ich zakresy
> plików są rozłączne. Do jednego biletu użyj `/implement`.

To nie jest szybszy `implement`. To inny kontrakt: dzieci nie pytają, nie commitują i nie są wiarygodne
same z siebie — wiarygodny jest dopiero odczyt plików po fali.

## Czego dowiodła praktyka (nie zgaduj tego ponownie)

Trzy zmierzone fakty, na których stoi cały skill:

1. **Dwa subagenty na jednym pliku gubią zapis po cichu.** Oba `apply_patch` zgłosiły sukces, końcowy
   plik zawierał tylko jedną zmianę. Sukces narzędzia nie jest dowodem zachowania zmiany.
2. **Równoległe commity na osobnych plikach przeszły** — ale w odstępie 5 sekund, więc to nie jest
   dowód odporności na prawdziwą równoczesność. Dlatego dzieci **nie commitują**; commits robi rodzic.
3. **Board daje widoczność, nie blokadę.** `board_post`/`board_read` pokazują, kto co robi, ale nie
   powstrzymają dwóch agentów przed tym samym plikiem. Board to ogłoszenia, nie zamek.

## 1. Preflight — bez tego nie startuj

```bash
git status --short          # brudne drzewo = STOP (fala na niezacommitowanych zmianach jest nieodwracalna)
git tag wave-backup-$(date +%Y%m%d-%H%M)   # punkt powrotu
```

Fala startuje tylko gdy: drzewo czyste, `docs/agents/` istnieje, bilety mają `Status: ready-for-agent`
i żaden nie ma otwartego pytania.

## 2. Podział na zbiory plików — jedyny prawdziwy warunek

Dla każdego biletu z frontieru ustal **zbiór ścieżek, które bilet dotknie**. Czytaj bilet, nie zgaduj
z tytułu. Zasady:

- Zbiory muszą być **rozłączne**. Nachodzą choćby jednym plikiem → te bilety idą w **różnych falach**,
  nie równolegle. To nie ostrożność: to wynik punktu 1 powyżej.
- Niepewny zbiór traktuj jako nachodzący. Bilet „dodaj pole do modelu" dotknie wspólnego schematu,
  choćby o tym nie pisał.
- **Bilety dotykające generowanych artefaktów idą zawsze szeregowo, po jednym**: `src/formulas/`,
  `*.bas`, `*.frm`, `*.xlsx`, `*.xlam`, eksporty skoroszytów. Równoległy zapis do pliku generowanego
  to nie konflikt merge'a, to uszkodzenie.
- Maksymalnie **3 bilety w fali**. Dokumentacja Kilo mówi „nie więcej niż cztery czy pięć"; Ty masz
  jeszcze review rano, a to jest wąskie gardło, nie tokeny.

Zapisz podział w `.scratch/<feature>/wave-<N>.md`: bilet, zbiór plików, kolejność. Ten plik jest
kontraktem fali i podstawą weryfikacji.

## 3. Manifest hashy — zabezpieczenie przed cichą utratą

Przed startem policz hash każdego pliku z sumy zbiorów:

```bash
git ls-files -z -co --exclude-standard -- <ścieżki> | xargs -0 sha256sum > .scratch/<feature>/wave-<N>.before
```

Po fali policz ponownie tą samą komendą (`.after`) i porównaj. Flaga `-co` jest istotna: `git ls-files` bez niej pomija nowe pliki, a dzieci najczęściej właśnie je tworzą. Oczekiwany wynik: każdy plik z manifestu `before`
zmieniony **tylko przez bilet, który go zadeklarował**, a żaden plik spoza deklaracji nie drgnął.
Rozbieżność = incydent: zatrzymaj falę, wskaż plik, nie commituj.

Bez tego manifestu nie odróżnisz „dziecko nic nie zrobiło" od „dziecko zrobiło i ktoś nadpisał".

## 4. Start fali

Jeden prompt, trzy zadania, żadnych pytań. Kontrakt dziecka musi być w prompcie, bo dziecko nie może
Cię o nic zapytać:

```
Wykonaj bilet <NN> z .scratch/<feature>/issues/<plik>.md.

Zasady:
- Dotykaj WYŁĄCZNIE tych plików: <lista>. Każdy inny plik to błąd — zatrzymaj się i zgłoś.
- Nie commituj, nie pushuj, nie zmieniaj gałęzi, nie ruszaj .git.
- Nie zadawaj pytań. Jeśli czegoś nie wiesz: zapisz to w polu "blocked" i zakończ.
- Nie uruchamiaj pełnego zestawu testów; uruchom testy dotyczące zmienionych plików.
- Przed edycją: board_post "START <NN> <pliki>". Po odczycie kontrolnym: board_post "RESULT <NN> <wynik>".

Zwróć wyłącznie:
{"ticket":"<NN>","files_changed":[...],"tests":{"ran":N,"passed":N,"failed":N},
 "blocked":"<powód albo null>","notes":"<max 3 linie>"}
```

Start: `task` z `background: true`, po jednym na bilet. Nie czekaj w turze — wynik wróci sam jako nowa
tura rodzica.

## 5. Weryfikacja rodzica — trzy odczyty, nie jeden

Gdy wyniki wrócą, dla każdego biletu:

1. **Odczytał pliki**, nie raport dziecka. Raport to deklaracja; plik to fakt.
2. **Sprawdź manifest** (`before` vs `after`) — czy zmieniło się dokładnie to, co zadeklarowano.
3. **Uruchom testy sam** dla zmienionych obszarów. Dziecko mogło nie mieć dostępu do czegoś, czego
   test wymaga.

Dopiero potem commit — po bilecie, jawnymi ścieżkami, bez `-A`. Jeśli dwa bilety zmieniły pliki w tej
samej fali (co znaczy, że podział był zły), commituj osobno i **zatrzymaj kolejne fale** do czasu
wyjaśnienia, który bilet jest właścicielem pliku.

## 6. Raport ranny

```
WAVE <N> — <data>
Bilety: <NN> zrobione | <NN> zablokowane
Commity: <sha> <bilet> <diff stat>
Testy: <co uruchomione> — <wynik>
Manifest: OK | rozjazd w <pliki>
Blokady: <bilet> — <czego potrzebuje>
Następna fala: <bilety, które się odblokowały> | brak
```

Pięć sekcji, żadnych esejów. Rano decydujesz, co merge'ujesz i w jakiej kolejności — skill nie
merge'uje i nie pushuje.

## 7. Kiedy nie używać fali

- Bilety nachodzą na siebie → `/implement`, bilet po bilecie.
- Jeden bilet, nawet duży → `/implement`; fala nie pomaga na rozmiar.
- Praca wymaga decyzji w trakcie → `/implement`; dziecko nie może zapytać, więc będzie zgadywać.
- Generowane artefakty w zakresie → szeregowo.
- Pierwszy raz w repo → jedna fala z **jednym** biletem, żeby zmierzyć czas i jakość, zanim puścisz trzy.

## 8. Fallback: worktree

Agent Manager (`agent_manager`, mode `worktree`) daje osobny checkout i branch per bilet. Używaj go
**tylko** gdy izolacja jest warta kosztu merge'a: jeden bilet psuje drzewo w trakcie, chcesz porównać
dwa podejścia, albo musisz oddać gałąź komuś innemu.

Worktree nie rozwiązuje problemu z punktu 1 — rozwiązuje go tylko w środku fali, a przenosi na merge.
Za to nie oddaje wyników do Twojej sesji: sesje Agent Managera są top-level, więc raport musisz
wyciągnąć sam.

<!-- next-step-pointer -->
> **Before you finish:** name the next step with the `co-dalej` skill (it reads the repo state
> and picks one), or state it yourself in one line with the exact command.
