# Odtworzenie obsługi pustego skoroszytu

Samodzielny przykład #120, bez oryginału, szablonu `.xlsm`, danych biznesowych, plików pomocniczych oraz uruchamiania setupu lub integracji. Obowiązuje instrukcja i źródła z tej samej rewizji Git. Użytkownik liczy jednostki w `Desk`, przegląda sumy wg tokenu w `Summary` i zaznacza ręcznie gotowość. `Ready` oznacza stan ręczny, nie świeżość zapytania. Wynik odtworzenia nie zastępuje kopii przypiętej wersją i SHA-256 w integracji.

**Sprawdzenie wstępne.** Z głównego katalogu repo uruchom `python examples/excel-reconstruction/preflight.py`. `READY` potwierdza wyłącznie dostępność wejść, nie poprawność skoroszytu ani kwalifikację. Brak wymaganego źródła blokuje odtworzenie; nie zastępuj go przypuszczeniem. Ten przykład używa kontrolki formularza na arkuszu i nie wymaga UserForm ani `.frx` (`companions` jest puste).

Jeśli dostosowany scenariusz wymaga pliku spoza Git, wpisz w `companions` jego `name`, niezmienną `version`, `sha256` (64 małe cyfry szesnastkowe) i bezpieczną instrukcję pozyskania `obtain` (bez poświadczeń). Pozyskaj plik ze wskazanego magazynu z kontrolą dostępu, umieść go poza Git jako `<katalog>/<version>/<name>` i dodaj `--companions <katalog>` do polecenia. Sprawdzenie nie pobiera ani nie kopiuje plików. Brak pliku lub pinu, albo różnica SHA-256 blokuje scenariusz. Przy imporcie UserForm traktuj źródło `.frm` i jego wymagany `.frx` jako jedną wersjonowaną całość.

**Bramki.** Celem jest desktopowy Excel Microsoft 365 na Windows z Power Query, slicerem dla tabeli i VBA, na odizolowanym pliku testowym. Przed otwarciem i zapisem użyj obowiązującego routera Excel do ustalenia zakwalifikowanego sposobu komunikacji z Excelem i osobnych zgód na wskazane operacje. Ładowanie zapytania może wykonać M już podczas konfiguracji; uzyskaj osobną zgodę na dostęp do wejść i wykonanie Power Query przed takim krokiem oraz przed późniejszym odświeżeniem. Przed kompilacją VBA i przed wykonaniem kodu uzyskaj odrębne zgody na oddzielne kopie. Jeżeli brakuje kwalifikacji, uprawnień lub umożliwiającej wykonanie konfiguracji zaufania, zatrzymaj dany krok. Nie obniżaj zabezpieczeń, nie zmieniaj konfiguracji globalnej i nie traktuj tego przykładu jako odbioru Kilo z #70.

## Instrukcja odtworzenia

1. Utwórz pusty skoroszyt i pozostaw dokładnie arkusze `Input`, `Desk`, `Summary`. Ustaw dla `Input!A:A` format `Text`, zanim wpiszesz tokeny, także w poszerzonej tabeli. W `Input!A1:B2` utwórz tabelę z nagłówkami `Token`, `Units` i jednym pustym wierszem. Ustaw nazwę tabeli `tblTokens`. Ziarno wejścia: jeden wiersz na wpis, token tekstowy (może się powtórzyć; `001` i `1` to różne klucze), `Units` jako liczba całkowita od `0` do `9999`. Wspierany zakres to najwyżej `100` wypełnionych wierszy, więc suma dla tokenu mieści się w `0..999900`, bez utraty dokładności w arkuszu. Wypełniony wiersz wymaga obu pól; pusty ma oba pola puste. Operator odpowiada za te granice; przykład nie waliduje wejścia interaktywnie.
2. W `Desk!A1` wpisz `Factor`, w `Desk!B1` liczbę `2`. Utwórz nazwę `UnitFactor` o zakresie skoroszytu, odwołującą się do `=Desk!$B$1`. W `Desk!A3:A7` wpisz kolejno `First`, `Adjustment`, `Constant`, `Gap`, `Last`. Wstaw poniższe zwykłe formuły A1 do pojedynczych komórek. Nie używaj wypełniania zakresu.

   | Komórka | Wpis |
   | --- | --- |
   | `Desk!B3` | `=Input!B2*UnitFactor` |
   | `Desk!B4` | `=Input!B3*UnitFactor+1` (wyjątek) |
   | `Desk!B5` | liczba `99`, bez formuły |
   | `Desk!B6` | pusta komórka |
   | `Desk!B7` | `=Input!B4*UnitFactor` |

3. Po sprawdzeniu zgód utwórz kolejno dwa puste zapytania. W Edytorze zaawansowanym wklej [`SourceTokens.m`](SourceTokens.m) do `SourceTokens` i wybierz `Only Create Connection`, bez Data Model. `SourceTokens` czyta wyłącznie `tblTokens` i pomija puste wiersze. Następnie wklej [`TokenTotals.m`](TokenTotals.m) do `TokenTotals` i załaduj wynik jako tabelę do istniejącego arkusza `Summary!$A$1`, bez Data Model. Nazwij tabelę `tblTokenTotals`. Oczekiwane kolumny: `Token` (tekst), `TotalUnits` (liczba całkowita), jeden wiersz na token; w tym kroku nie ma jeszcze wpisów, więc nie ma wyników do utrwalenia. Wyłącz odświeżanie przy otwarciu, okresowe odświeżanie i odświeżanie w tle dla połączeń, jeśli dostępne; przed ponownym otwarciem potwierdź brak automatycznego wykonania.
4. W `Summary!D1` wpisz `Not refreshed`. Przed zmianą `tblTokens` lub rozpoczęciem odświeżania operator ustawia tam `Not current`. Dopiero po udanym odświeżeniu `TokenTotals` i sprawdzeniu jego wyniku wpisuje `Current`; po błędzie wpisuje `Refresh failed - not current`, nawet jeśli poprzednie wiersze są nadal widoczne. W `Summary` zaznacz `tblTokenTotals`, wstaw slicer dla pola `Token` i umieść go obok wyników, w okolicy `D3`, bez zasłaniania tekstu stanu. Ma filtrować tę jedną tabelę, nie `tblTokens` ani `Desk`. Nie twórz tabeli przestawnej ani połączenia z modelem.
5. W `Desk!D2` wpisz `Status`, w `Desk!E2` wpisz `Pending`. Zaimportuj [`Reconstruction.bas`](Reconstruction.bas) jako moduł standardowy `Reconstruction`. Wklej [`Desk.vba`](Desk.vba) do istniejącego modułu dokumentu arkusza `Desk` (`View Code` z karty arkusza), nie do nowego modułu klasy. Dodaj na `Desk` w okolicy `D4` przycisk typu `Form Control` opisany `Mark ready` i przypisz `Reconstruction.MarkReady` z tego samego skoroszytu. Nie ma zdarzeń `Workbook_Open`, odwołań zewnętrznych ani zależności od dodatków.
6. Z pustą `tblTokens`, bez uruchamiania zdarzenia lub makra na pliku wyjściowym, zapisz nowy, oddzielny plik `.xlsm` poza Git i zamknij go. Wykonaj osobne kopie tego zamkniętego pliku do ponownego odczytu i prób (poniżej). Nie nadpisuj innych skoroszytów. Dane testowe i wyniki wprowadzaj po ponownym otwarciu kopii i nie zapisuj ich. Jeżeli próba się nie powiedzie, pozostaw plik wyjściowy bez zmian i powtórz na świeżej kopii po usunięciu blokady.

## Scenariusze odbioru

Po ponownym otwarciu zweryfikuj z instrukcją arkusze, tabele, zakres nazwy, dokładne formuły i ich wyjątki, kod i miejsca ładowania obu zapytań, oba moduły, przypisanie przycisku i zakres slicera. To potwierdza trwałość struktury, nie działanie. W próbach formuł i Power Query pozostaw kod VBA wyłączony; ręczna kompilacja i próba działania VBA mają osobne kopie.

Do prób formuł i Power Query zmień rozmiar `tblTokens` na `Input!A1:B4` poleceniem `Resize Table`, bez wstawiania wierszy arkusza. Następnie wpisz jawnie syntetyczne wartości w kolejności od `Input!A2`:

| Token | Units |
| --- | ---: |
| Amber | 2 |
| Blue | 7 |
| Amber | 3 |

| Próba po ponownym otwarciu | Oczekiwane zachowanie |
| --- | --- |
| Przelicz `Desk` dla `UnitFactor = 2`; zmień `Desk!B1` na `3` i przelicz ponownie. | `B3`, `B4`, `B7`: odpowiednio `4`, `15`, `6`, potem `6`, `22`, `9`. `B5` pozostaje liczbą `99` bez formuły, `B6` pozostaje naprawdę pusta, a `B4` zachowuje formułę z `+1`. |
| Ustaw `Not current`; po zgodzie odśwież tylko `TokenTotals` (wykonuje zależność `SourceTokens`) i poczekaj na zakończenie. | Dwa wiersze w `tblTokenTotals` od `Summary!A1`: `Amber` z `TotalUnits = 5` i `Blue` z `TotalUnits = 7`. `SourceTokens` nadal ma tylko połączenie; bez Data Model i bez innych miejsc ładowania. Po potwierdzeniu wyniku wpisz `Current`. |
| Po udanym odświeżeniu wybierz `Amber` na slicerze; wyczyść filtr. | Widać wyłącznie `Amber` z sumą `5`, a po wyczyszczeniu oba wiersze. `Input` i `Desk` bez zmian. Bez tej próby wynik scenariusza slicera nie jest zaliczony. |
| Na świeżej kopii ustaw `Not current`, zmień rozmiar `tblTokens` do `Input!A1:B3`, wpisz ręcznie `001` z `Units = 2` i `1` z `Units = 7` w tekstowej kolumnie `Token`. Po zgodzie odśwież `TokenTotals`. | Dwa osobne wiersze: `001` z sumą `2`, `1` z sumą `7`. Po sprawdzeniu wpisz `Current`. |
| Na świeżej kopii ustaw `Not current`, zmień rozmiar `tblTokens` do `Input!A1:B101`, wpisz `100` wierszy `Amber` z wartością `9999` i po zgodzie odśwież `TokenTotals`. Ustaw `Not current`, zastąp wszystkie `Units` zerami i po osobnej zgodzie odśwież ponownie. | W obu przypadkach jeden wiersz `Amber`, najpierw z sumą `999900`, potem `0`. Po każdym potwierdzonym wyniku wpisz `Current`. |
| Na kopii po udanym odświeżeniu ustaw `Not current`, zmień nazwę tabeli `tblTokens` na `tblTokensMissing`; za osobną zgodą ponów odświeżenie `TokenTotals`. | Odświeżenie zgłasza błąd brakującego źródła. Status po reakcji operatora: `Refresh failed - not current`. Jeżeli poprzedni wynik nadal jest widoczny, ten status pozostaje widoczny obok niego. Zamknij kopię bez zapisu. |
| Na osobnej kopii, za zgodą na kompilację, w VBE wybierz `Debug > Compile`. | Projekt kompiluje się bez błędów. Zapis pliku ani odczyt modułu nie dowodzi kompilacji. |
| Na osobnej kopii, za zgodą na wykonanie kodu, kliknij `Mark ready`, zmień `Desk!B1` na `3`, kliknij ponownie i zmień `Desk!A1`. | `Desk!E2` kolejno `Ready`, `Pending`, `Ready`, `Ready`. Przycisk ustawia tekst stanu, zdarzenie resetuje go po zmianie parametru, ale nie po zmianie etykiety. Próba nie uruchamia Power Query. |

**Dowód i decyzja.** Zapisz rewizję źródeł, faktyczny build Excela, zakres zgód oraz osobne statusy i obserwacje dla sprawdzenia wstępnego, ponownego odczytu, formuł, Power Query (sukces i awaria), slicera, kompilacji i interakcji VBA. Publikuj wyłącznie zredagowane statusy i opis zgodności z oczekiwaniami, nie plik, dane z arkuszy, wyniki zapytań ani poświadczenia. Desktop jest `NOT_RUN` do uzyskania zgody; brak obowiązkowego elementu daje `BLOCKED`, a wynik próby różny od oczekiwanego daje `FAIL`. Odbiór dotyczy zgodności zachowania ze specyfikacją, nie wyglądu, identyczności pliku lub automatycznego zbudowania skoroszytu.

**Testy przenośne.** `python -B -m unittest discover -s examples/excel-reconstruction -v` sprawdza gotowość źródeł oraz blokady brakującego źródła, niewłaściwej wersji i niezgodnego SHA-256 syntetycznego pliku pomocniczego. Nie wykonuje formuł, M ani VBA i nie zapisuje ani nie otwiera skoroszytu.
