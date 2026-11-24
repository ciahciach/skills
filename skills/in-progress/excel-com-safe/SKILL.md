---
name: excel-com-safe
description: "Use when direct Excel COM via pywin32 is explicitly selected on Windows. Covers dedicated instances, safe workbook operations and bounded synthetic probes for formulas and native VBA UserForms."
metadata:
  version: "1.0.0"
  category: office
  platform: windows
---

# Excel COM: bezpieczna automatyzacja

## Kiedy
Stosuj po wyborze bezpośredniej ścieżki COM (`win32com.client`), nie jako automatyczny fallback. Jeśli obowiązuje `excel-router`, zastosuj jego kontrole przed operacją. Wybór recepty nie jest zgodą na zapis ani zmianę ustawień.

## Reguły startu
1. Użyj `DispatchEx("Excel.Application")`, nie `Dispatch`. Pracuj tylko we własnej instancji.
2. Ustaw `Visible=False`. Zmieniaj `DisplayAlerts` i `ScreenUpdating` tylko na czas potrzebnej fazy. `DisplayAlerts=False` nie zabezpiecza przed skutkami otwarcia ani nadpisaniem pliku.
3. Po `Workbooks.Open` czekaj na `Application.Ready` najwyżej 20 s, z odstępem 1 s. Brak gotowości zgłoś jako blokadę.
4. W `finally` zamknij własny skoroszyt z jawnym `SaveChanges`, następnie wykonaj `app.Quit()` i zwolnij referencje COM. Nie zamykaj procesu użytkownika.

## Zanim otworzysz plik
- Potwierdź ścieżkę i sprawdź plik blokady `~$` obok skoroszytu. Jeśli istnieje, nie otwieraj skoroszytu.
- Dla odczytu bez makr zapamiętaj `AutomationSecurity`, ustaw `ForceDisable` bezpośrednio przed `Workbooks.Open(UpdateLinks=0, ...)` i przywróć zastaną wartość w `finally`, również po błędzie. Wyłącz zdarzenia na czas operacji i przywróć ich zastany stan. `UpdateLinks=0` nie blokuje XLM ani odświeżenia połączeń; sprawdź profil przed `Open`.
- Zachowaj format źródłowy i pracuj na kopii roboczej. Zapis weryfikuj przez niezależne ponowne otwarcie bez zapisu.

## Syntetyczny test zapisu formuły
Dla kwalifikacji jednej zwykłej formuły na syntetycznym XLSX użyj `py -3.14 -B -X utf8 scripts/qualify-excel-com.py` z rewizji zawierającej runner wskazany w [#40](https://github.com/ciahciach/skills/issues/40). Nie podawaj własnego pliku. Runner rozdziela no-op, dry-run, zapis i niezależny odczyt. Wynik tego testu nie potwierdza obsługi UserForm ani zgody na zapis pliku użytkownika.

## Syntetyczna próba natywnego UserForm
Sprawdzony zestaw: desktop Excel `16.0.20527.20194` (build `20527`) i pywin32 `312`. Użyj COM tylko po akceptacji tej ścieżki. W dedykowanej instancji `DispatchEx` utwórz nowy syntetyczny skoroszyt przez `Workbooks.Add(-4167)` (`xlWBATWorksheet`, bez szablonu użytkownika). Bez pliku docelowego, produkcyjnych powiązań, zmian Trust Center, rejestru ani trwałych zmian zabezpieczeń. Jeśli konfiguracja blokuje dostęp do `VBProject` lub wykonanie VBA, zgłoś blokadę zamiast ją obchodzić.

1. **Utwórz i zapisz.** Dodaj `wb.VBProject.VBComponents.Add(3)` (`vbext_ct_MSForm`). Ustaw wymiary przez właściwości komponentu VBIDE, nie przez `Designer.Width` / `Designer.Height`:
   ```python
   form.Properties.Item("Width").Value = width_pt
   form.Properties.Item("Height").Value = height_pt
   ```
   Dodawaj kontrolki najwyższego poziomu przez `form.Designer.Controls`, a dzieci ramki przez `frame.Controls`. W standardowym module dodaj procedurę testową, która wywołuje logikę formularza i zapisuje wyniki scenariuszy w komórce syntetyku. Zapisz przez `wb.SaveAs(path, FileFormat=52)` pod nieistniejącą ścieżką `.xlsm` w unikalnym katalogu próby pod `%TEMP%\kilo\`. Potwierdź zapis. W `finally`, po zamknięciu obu instancji użytych w próbie, usuń wyłącznie jej artefakty.
2. **Jeśli sprawdzasz kompilację, zrób to przed wykonaniem VBA.** Przed `CompileProject` poczekaj na gotowość VBE i potwierdź, że `Application.VBE.ActiveVBProject` to projekt syntetyku. Raportuj pełną kompilację osobno. Samo wywołanie polecenia, stan przycisku ani udane `Application.Run` nie dowodzą sukcesu. Jeśli polecenie pozostaje aktywne lub brak jednoznacznego wyniku w budżecie próby, zapisz `NOT VERIFIED`. Jawny błąd kompilacji zgłoś jako błąd, bez ponawiania w pętli.
3. **Sprawdź wykonanie VBA.** W instancji autora, bez ponownego otwierania z włączonymi makrami, uruchom wyłącznie procedurę syntetyku, np. `app.Run(f"'{wb.Name}'!Probe.RunFixture")` dla modułu `Probe` i procedury `RunFixture`. Porównaj odczytane wyniki (np. walidacji i resetu) z oczekiwaniami. Zapisz je przez `wb.Save()` i zamknij instancję. To dowód wykonania scenariuszy, nie pełnej kompilacji ani fizycznych kliknięć lub fokusu.
4. **Sprawdź trwałość niezależnym odczytem.** Otwórz zapisany plik w drugiej instancji `DispatchEx` z `ReadOnly=True`, `UpdateLinks=0` i `AutomationSecurity=ForceDisable` na czas otwarcia. Potwierdź komponent, wymiary z VBIDE, nazwy, podpisy i względne `TabIndex`. Sprawdź oczekiwane dzieci w `Controls` każdej ramki osobno, także dla zagnieżdżonych ramek. `Designer.Controls` może zawierać potomków: nie używaj jego łącznej liczby do potwierdzania rodzica ani nie licz tych samych kontrolek drugi raz. Odczytaj zapisany wynik procedury i zamknij bez zapisu.

[Dowody próby A/B/C](https://github.com/ciahciach/skills/issues/14#issuecomment-7111891357): utworzenie i zapis, niezależny odczyt (w tym dwie ramki) oraz wykonanie scenariuszy VBA potwierdzone; pełna kompilacja VBE `NOT VERIFIED`. Próba nie potwierdza interakcji klawiaturą/myszą, zgodności wizualnej, XLSB/XLAM ani gotowości do pracy na pliku produkcyjnym.

## Mapa błędów
| Kod lub objaw | Reakcja |
|---|---|
| `-2147352567` przy `Open` | Zamknij własną instancję, odczekaj 2 s i spróbuj w nowej. Najwyżej trzy próby; nie ponawiaj zapisu o nieznanym wyniku. |
| `-2146827284` przy `NumberFormat` | Sprawdź scalenia i ochronę zakresu. Nie obchodź ochrony ani nie rozscalaj poza uzgodnionym zakresem. Ustawiaj format na docelowym `Range`, nie na wszystkich `Cells` arkusza. |
| `Open method of Workbooks class failed` | Sprawdź plik blokady, uprawnienia i ścieżkę. |
| `SetForegroundWindow` | Nie aktywuj okien. Do operacji COM nie potrzebujesz fokusu. |

## Budżet
Najwyżej trzy próby na operację, potem STOP i raport z krokiem, ścieżką i kodem błędu. Nie stosuj nieskończonej pętli.
