## Standard jakości Excel

Wersja: `excel-v1`

Dla autora i osi Standards w `code-review`: używaj sekcji z ocenianej rewizji projektu, bez pobierania nowszych reguł. Standard dotyczy formuł i projektu arkuszy, architektury skoroszytu, Power Query M i VBA, w tym ich współdziałania. Poza zakresem są Data Model, DAX, pełny audyt dostępności i ocena poufności przy udostępnianiu. Istniejące zasady ochrony danych nadal obowiązują.

### Wymagania

Wymagany dowód nie jest zgodą na operację. Dla skoroszytu objętego kontraktem `setup-excel-repo` przestrzegaj jego bramek: osobna zgoda przed każdym dostępem do danych i odświeżeniem, także przy otwarciu z automatycznym odświeżeniem, diagnostyce i ponowieniu. Zalogowanie nie zastępuje zgody. Kompilację i uruchomienie VBA kwalifikuj i autoryzuj osobno, wykonując je na oddzielnych kopiach testowych zgodnie z kontraktem. Wstrzymaj operację bez wymaganej zgody lub kwalifikacji.

**EX-FRESH: świeżość i okres.** Wynik deklarowany jako aktualny musi odpowiadać deklarowanemu okresowi i stanowi wszystkich wymaganych wejść. Stary wynik może pozostać dostępny, jeżeli jego faktyczny okres i stan są widoczne, a częściowe lub nieudane odświeżenie nie wygląda na sukces. Dla zmiany wpływającej na odświeżanie sprawdź wynik u odbiorcy po pełnym odświeżeniu wymaganych wejść oraz po istotnej awarii, np. zatrzymaniu jednego z nich. Kwietniowa sprzedaż przeliczona po majowym kursie nie jest aktualnym raportem za maj.

**EX-CONTRACT: kontrakt warstw.** Określ i zachowaj to, na czym polega odbiorca danych: wymagane pola, typy, dozwolone puste wartości, kulturę, okres, ziarnistość i klucze tam, gdzie mają znaczenie. Przy zmianie kontraktu znajdź wszystkie dotknięte użycia, również poza diffem, i dostosuj te, które zmiana psuje. Przykład: po zmianie `Net` na `NetAmount` sprawdź zapytania, formuły, nazwy i wywołania VBA korzystające z kolumny. Po `Merge` sprawdź, czy duplikat klucza nie mnoży wierszy i nie zawyża sumy. Nie wymagaj niezwiązanych porządków w istniejącej logice.

**EX-TARGET: zgodność z Excelem odbiorcy.** Ustal wspierane wersje i platformy. Wykaż działanie potrzebnych funkcji w docelowych środowiskach, których dotyczy zmiana, np. przeliczenia formuły, odświeżenia z właściwym konektorem i miejscem ładowania albo uruchomienia makra. Samo otwarcie `.xlsm` w przeglądarce nie potwierdza, że zadziała przycisk VBA.

**EX-ACCESS: podstawowa dostępność.** W arkuszu użytkowym przekaż istotny status także bez koloru, np. dodaj tekst `Błąd odświeżenia` do czerwonego oznaczenia. Oceniaj zmieniony interfejs i dotknięte użycia, nie cały skoroszyt.

### Zalecenia

- **Formuły i projekt arkuszy.** Dla identyfikatora preferuj dokładne dopasowanie i sprawdź znaczenie braku dopasowania, duplikatu, pustej wartości i zera. Nie traktuj `IFERROR(...,0)` jako domyślnego zamiennika jawnego błędu. Dopasowanie przybliżone jest użyteczne np. dla progów rabatowych o określonych granicach. Wybieraj czytelne `XLOOKUP`, `LET` i `FILTER` tam, gdzie są wspierane i upraszczają pracę. Rozważ `INDEX` + `MATCH(...,0)`, kolumnę pomocniczą lub filtr tabeli dla starszego Excela; filtr tabeli daje widok, nie osobny wynik. Unikaj scaleń w danych i polach wejściowych, np. użyj zawijania tekstu zamiast scalania nagłówków.
- **Architektura skoroszytu.** Dla rosnącego rejestru preferuj tabelę i odwołania strukturalne, dla parametru o stałym rozmiarze nazwany zakres. Dla krótkiej stałej listy wystarczy jawne źródło walidacji; rosnąca lista może korzystać z tabeli bez nagłówka wśród opcji. Wynik rozlewany potrzebuje miejsca poza tabelą, także przy wzroście. Arkusz techniczny, nagłówki w pierwszym wierszu arkusza czy dwie puste kolumny między blokami to konwencje, nie reguły Excela. Oceniaj rzeczywistą kolizję, nie położenie `B5`.
- **Power Query M.** Oceniaj osobno kontrakt wyniku, czytelność kodu, sposób wykonania i miejsce ładowania. Nazywaj kroki według roli; rozdziel pobranie, przygotowanie i wynik, jeśli ułatwia to zrozumienie lub ponowne użycie. Przy konwersji tekstu uwzględnij kulturę źródła; dla opcjonalnego pola `null` może mieć sens, dla wymaganego może ukryć naruszenie kontraktu. Brak foldingu nie jest sam w sobie defektem: koszt i możliwość delegowania zależą od konektora i kroków. Nie dodawaj `Table.Buffer` domyślnie; porównaj koszt przy równoważnym wyniku. Przy zmianie wpływającej na wynik zweryfikuj odświeżenie i faktyczny cel ładowania, np. tabelę w arkuszu, nie sam podgląd edytora.
- **VBA.** Preferuj `Option Explicit`, jawne typy, wyraźny cel operacji (`Workbook`, `Worksheet`, kwalifikowane `Range` i `Cells`) i wąskie handlery zdarzeń. `ThisWorkbook` może oznaczać dodatek, a `Activate` może być celowe, gdy zmiana widoku należy do zadania. Jeśli procedura zmienia stan `Application`, zachowaj i przywróć wartości sprzed wywołania także po błędzie. Przykład: bezwarunkowe `EnableEvents = True` nie przywraca poprzedniego `False`. Sprawdź wielokomórkowe wejście i ścieżkę błędu, jeśli zmiana ich dotyczy.

Te wzorce pomagają spełnić wymagania. Ich pominięcie jest uwagą, nie samodzielną podstawą blokady. Jeśli skutkiem jest np. wynik sprzeczny z kontraktem, wskaż naruszone wymaganie, nie konwencję.

### Dowody i decyzja w review

**EX-EVIDENCE (wymaganie): dobierz dowód do twierdzenia.** Zapisz ocenianą rewizję, środowisko, scenariusz, oczekiwanie i obserwację w zakresie potrzebnym do rozstrzygnięcia. Raportuj osobno:

- **Inspekcję statyczną** aktualnego eksportu i odniesień: co widać w kodzie, schemacie lub układzie. Może dowieść np. niepoprawnego odwołania, ale nie wykonania makra.
- **Kompilację VBA**: osobny wynik `VBE > Debug > Compile` w wskazanym środowisku. Odczyt kodu i udany import nie dowodzą kompilacji; kompilacja nie dowodzi działania zdarzenia ani skutku makra.
- **Próbę działania**: odczyt faktycznego rezultatu po danym przeliczeniu, odświeżeniu albo uruchomieniu w docelowym Excelu. Samo otwarcie, cache, zielony podgląd Power Query i zapisany import nie dowodzą aktualnego wyniku. Jeśli zmiana dotyczy działania, sprawdź odpowiednią ścieżkę, nie tylko fakt, że operacja nie zgłosiła błędu.

Automatyzuj weryfikację tam, gdzie można; jednorazowa próba może wystarczyć bez stałego CI. Człowiek wykonuje tylko potrzebny krok HITL, a wykonawca zapisuje dowód. Gdy potwierdzono, że odświeżenie wymaga logowania do SharePoint, którego brakuje, odnotuj `BLOCKED` i wskaż logowanie jako krok HITL. Po zalogowaniu i potwierdzeniu wymaganych zgód ponów odświeżenie i sprawdź wynik. Przy niewyjaśnionym timeout odnotuj `BLOCKED` i potrzebę diagnozy lub ponowienia próby; nie przypisuj przyczyny poświadczeniom ani kodowi M bez dowodu.

Przy każdym blokującym ustaleniu podaj regułę, stosowalność, dowód lub jego brak i następny krok. Rozróżnij **potwierdzone naruszenie** (obserwacja przeczy wymaganiu) od **zgodności niepotwierdzonej** (brak wymaganego dowodu). Oba wstrzymują akceptację w review; brak dowodu nie jest `PASS`. Ocena ogranicza się do zmiany i wszystkich jej dotkniętych odniesień.

Jeżeli wskazane rozwiązanie ma istotny koszt lub szkodę, zaproponuj miejscową alternatywę zachowującą cel wymagania. Po jawnym zatwierdzeniu przez dewelopera automat zapisuje w PR zakres odstępstwa, regułę, uzasadnienie, alternatywę, dowód osiągnięcia celu i zatwierdzającego. Zmiana celu wymaga osobnego uzgodnienia ze zlecającym.

Akceptacja w review nie zastępuje odbioru przez użytkownika ani nie uruchamia i nie autoryzuje integracji skoroszytu po merge.
