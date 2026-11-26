# Próba review standardu Excel v1

**Zakres:** #114. [Kanoniczna sekcja](../../skills/in-progress/setup-excel-repo/excel-standard.md) jest jedynym źródłem reguł. Poniżej są dane próby i wynik oceny, nie dodatkowy standard.

## Jak powtórzyć

1. Weź sekcję `excel-v1` z ocenianej rewizji. W próbie potraktuj jej treść jako lokalną sekcję w głównym `CODING_STANDARDS.md` projektu testowego. Nie uruchamiaj setupu i nie pobieraj reguł z forka.
2. Zastosuj [oś Standards](../../skills/engineering/code-review/SKILL.md) do każdego wiersza tabeli jako osobnej zmiany. Podaj recenzentowi wyłącznie wejścia, bez wyników. Poproś o regułę, stan dowodu, decyzję i następny krok. Nie dopowiadaj obserwacji, których nie ma we wejściu.
3. Porównaj jego odpowiedzi z wynikami poniżej. `PASS` całej próby oznacza, że recenzent poprawnie rozróżnił przypadki, także te, które wstrzymują review. Nie oznacza zweryfikowania prawdziwego skoroszytu.

Aby odtworzyć wcześniejsze przebiegi, użyj wejść podanych w zapisie poniżej, a nie ich wariantów z pełnej próby. W RED zacznij od podanej bazy bez sekcji Excel; oczekuj cytatu z lokalnej reguły, nie tylko diagnozy. W dwóch częściowych przebiegach z sekcji przekaż wyłącznie akapit `EX-FRESH` z jej przypiętego bloba (akapit nie zmienił się). W pełnej próbie użyj wszystkich reguł; w G podaj dodatkowo lokalne wymaganie z opisu przypadku.

## Wynik

**RED:** Na bazie `4733802d3b46efb692a719cc5a21b7ba43b64ef3` niezależny recenzent rozpoznał problem z A, ale nie mógł wskazać wersjonowanej reguły. Obecny kontrakt setupu mówił o aktualności eksportu, nie o aktualności wyniku po odświeżeniu. Po dodaniu samego `EX-FRESH` ponowna próba A wskazała regułę i potwierdzone naruszenie; osobna próba E nadal nie mogła wskazać reguły blokującej przy braku dowodu działania przycisku.

**GREEN:** Niezależny recenzent zastosował istniejącą oś Standards do poniższych wejść z pełną sekcją `excel-v1`. Ocena tekstowa, bez uruchomienia Excela, otwierania skoroszytu czy logowania. Obserwacje ze środowiska wykonania w tabeli są syntetycznymi danymi wejściowymi, nie wynikami działania Excela w ramach #114.

## Zapis przebiegów

Identyfikatory przebiegów w Kilo i cytaty z odpowiedzi recenzentów:

- RED A, `ses_de7c3fff7ffeDdJAXoDHkN1WTZ`: zmieniony `Report` mnoży `Sales` przez `FX`. Po próbie odświeżenia `Sales` jest z kwietnia, bo odświeżenie nie powiodło się, `FX` jest z maja, a raport pokazuje `Aktualny: maj`. Odpowiedź: „Baseline pozwala opisać tę niespójność, ale nie pozwala zaklasyfikować jej jako potwierdzonego naruszenia lokalnej reguły Excel v1, ponieważ nie ma takiej reguły do zacytowania.”
- Tylko `EX-FRESH`, wariant A, `ses_de7c36f27ffekCQuHk8ancHcYl`: `Report` zmienia `SUM(Sales[Net])` na `SUMPRODUCT(Sales[Net], FX[Rate])`. UI pokazuje `Aktualny: maj`, ale log wykazuje nieudane odświeżenie `Sales` i kwietniowe wiersze oraz udane odświeżenie majowego `FX`. Odpowiedź: „Potwierdzone naruszenie `EX-FRESH`. Deklaracja aktualności za maj nie odpowiada stanowi obu wymaganych wejść.”
- Tylko `EX-FRESH`, wariant E, `ses_de7c32611ffeBoG3dGpJe6fSrj`: zmieniony handler przycisku; odczytano aktualny eksport, `VBE Compile` przeszło w Excelu desktopowym. W docelowym Excelu arkusz się otwiera, ale nie zaobserwowano działania przycisku. Odpowiedź: „Standards może więc rozróżnić te wyniki, ale nie ma podstawy w tej wersji standardu, by uznać brak obserwacji działania przycisku za blokujący.”
- GREEN, `ses_de7b82d74ffeYJv29sTJ9w9ksa`, blob sekcji `21515fb981ae209417bf6e3178e6c0aa0f69c9e4` (`git show 21515fb981ae209417bf6e3178e6c0aa0f69c9e4`): „10/10 decyzji zgodnych z zapisanymi wynikami Standards. Niezależne decyzje ustaliłem przed odczytem wyników porównawczych.”
- GREEN G, odpowiedzi dla trzech wariantów: z zatwierdzeniem i obserwacją „Bez blokady”; bez zatwierdzenia „Potwierdzone naruszenie `LOCAL-STATUS`”; bez obserwacji „Zgodność niepotwierdzona”.

## Scenariusze i wyniki

| Przypadek i wejście | Zaobserwowana decyzja Standards |
| --- | --- |
| A. `Report`: `+ Status = "Aktualny: maj"`. Raport korzysta z kwietniowego `Sales` po jego nieudanym odświeżeniu i majowego `FX` po udanym odświeżeniu. | `EX-FRESH`: potwierdzone naruszenie. Pokaż faktyczny okres i stan; sprawdź wynik po pełnym odświeżeniu i awarii wejścia. |
| B. Wynik M: `Net` zmieniono na `NetAmount`. Niezmieniony odbiorca `Summary!B2` nadal ma `SUM(Sales[Net])`. | `EX-CONTRACT`: statycznie potwierdzone naruszenie poza diffem. Dostosuj odbiorcę lub zachowaj kontrakt; sprawdź dotknięte odwołania. |
| C. Tabela techniczna zaczyna się w `B5`; próba wzrostu nie wykazuje kolizji; brak lokalnej reguły położenia. | Konwencja architektury, bez blokady. Nie przenoś tabeli ze względu na adres. |
| D. Wymagane wyszukiwanie identyfikatora zmieniono na `XLOOKUP`. Docelowy Excel 2019 na Windows otwiera plik, ale macierz zgodności dla próby wyklucza tę funkcję. | `EX-TARGET`: potwierdzone naruszenie; samo otwarcie nie dowodzi przeliczenia. Zastosuj wspieraną alternatywę i sprawdź wynik w docelowym Excelu. |
| E. Zmieniono `PostOrder_Click`. Odczytano eksport, `VBE > Debug > Compile` przeszło w docelowym Excelu; brak próby przyciskiem. | `EX-TARGET`, `EX-EVIDENCE`: zgodność niepotwierdzona, nie potwierdzone naruszenie. Przytrzymaj akceptację i sprawdź faktyczny skutek kliknięcia. |
| F1. Odświeżenie staje na jawnym żądaniu logowania do organizacyjnego SharePoint; potwierdzono wylogowanie. Skoroszyt jest objęty kontraktem `setup-excel-repo`; brak potwierdzenia zgody na ponowienie. | `EX-FRESH`, `EX-EVIDENCE`: `BLOCKED`; logowanie to krok HITL, nie zgoda na dostęp lub odświeżenie. Wstrzymaj ponowienie do potwierdzenia odrębnej zgody. |
| F2. Odświeżenie przekracza limit czasu, przyczyna nieznana. Skoroszyt jest objęty kontraktem `setup-excel-repo`; brak zgody na ponowienie lub dalszy dostęp do danych. | `EX-FRESH`, `EX-EVIDENCE`: `BLOCKED`; nie przypisuj awarii poświadczeniom ani M. Można ocenić istniejące logi bez nowego dostępu; wstrzymaj diagnostykę wymagającą dostępu do danych oraz ponowienie, aż odrębna zgoda obejmie daną operację. |
| G. Lokalne `LOCAL-STATUS` wymaga pełnego napisu `Błąd` w każdej zmienionej komórce statusu, by status był rozpoznawalny bez koloru. Dla jednej kolumny stałej szerokości napis zasłaniał sąsiednią wartość. Diff zastępuje napis `Błąd` w komórce glifem `!` i dodaje widoczną legendę nad kolumną. Próba w docelowym Excelu potwierdza identyfikację błędu bez koloru i czytelność sąsiedniej wartości. Deweloperka Marta jawnie zatwierdziła odstępstwo dla tej kolumny; PR zapisuje regułę, zakres, powód, alternatywę, dowód i zatwierdzającą. Powtórz ocenę bez zatwierdzenia i, osobno, bez obserwacji. | Zatwierdzone miejscowe odstępstwo od `LOCAL-STATUS`, zachowany cel i spełnione `EX-ACCESS`: bez blokady z kompletem dowodów. Bez zgody potwierdzona rozbieżność z `LOCAL-STATUS` blokuje; bez obserwacji zachowanie celu pozostaje niepotwierdzone i odstępstwo nie zamyka blokady. |
