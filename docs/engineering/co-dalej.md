## What it does

Wskazuje jeden następny krok dla konkretnego Issue, PR-a, grafu lub skoroszytu. Podaje dowód rozstrzygający o gotowości albo wskazuje, czego jeszcze nie potwierdzono. Niczego nie wykonuje.

## When to reach for it

W Kilo VS Code otwórz checkout tego forka i wpisz `/co-dalej #75` lub podaj link do Issue, PR-a albo raportu odbioru. Polecenie czyta instrukcję z tego checkoutu; nie wymaga instalowania skilla globalnie i nie jest częścią pluginu Claude Code.

## Common questions

**Czy zielony PR oznacza, że można ruszyć z zależnym Issue?** Nie. W profilu Kilo liczy się potwierdzony merge wymaganej zmiany do właściwej bazy. Częściowy PR nie potwierdza wykonania całego Issue.

**Czy merge kodu M kończy pracę nad skoroszytem?** Nie. Autoryzacja integracji, weryfikacja zapisanej kopii i jej jawny odbiór to odrębne warunki. Przy zmianie struktury może być wymagana również wyłączność zapisu.

## It's working if

1. W checkoutcie z tą zmianą użyj `/co-dalej <link-do-Issue>` w Kilo VS Code. W śladzie oczekuj odczytu repozytoryjnego `SKILL.md`, jednego następnego kroku ze wskazaniem dowodu i braku uruchomienia tego kroku.
2. W tym samym checkoutcie zleć review aktualnego diffu, wskazując wprost `skills/engineering/code-review/SKILL.md` z tego checkoutu zamiast globalnego skilla. W śladzie sprawdź odczyt tego pliku. Po zakończeniu w śladzie nie powinno być wywołania ani odczytu `co-dalej`.

Kontrola frontmatter i taki test instrukcji poza UI nie potwierdzają przebiegu w rozszerzeniu VS Code.

## Where it fits

To samodzielna komenda, nie etap kończący inne skille. [Ask Matt](https://aihero.dev/skills-ask-matt) pokazuje ogólną mapę skilli, a `/granica` pomaga zdecydować, co zrobić z kontekstem na granicy etapów.
