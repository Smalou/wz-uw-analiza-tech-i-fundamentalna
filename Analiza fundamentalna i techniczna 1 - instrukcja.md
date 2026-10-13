# Analiza losowości i sezonowości stóp zwrotu WIG20: instrukcja i objaśnienie

Plik: `Analiza fundamentalna i techniczna 1.py`

## 1. Cel skryptu

Skrypt bada, czy **dzienne stopy zwrotu indeksu WIG20** w okresie **01.01.2016–31.07.2026**:

1. zachowują się **losowo**, czyli czy przeszłe stopy zwrotu nie pomagają przewidywać przyszłych (słaba forma efektywności rynku),
2. mają **rozkład normalny**,
3. są **stacjonarne**,
4. wykazują **efekty kalendarzowe**: efekt dnia tygodnia i efekt miesiąca roku.

Na koniec zapisuje wyniki do pliku Excel i pięciu wykresów PNG.

---

## 2. Jak uruchomić

### 2.1. Wymagane biblioteki

Na tym komputerze (Python 3.13) bibliotek jeszcze nie ma. Instalacja:

```bash
pip3 install pandas numpy scipy statsmodels seaborn matplotlib openpyxl requests
```

> `requests` i `io` są importowane, ale używa ich tylko zakomentowany kod pobierający dane ze Stooq. Bez `requests` skrypt i tak się nie uruchomi, bo import stoi na początku pliku.

### 2.2. Plik z danymi (ważne)

Skrypt wczytuje plik **`wig20_d.csv`** (linia 109):

```python
df = pd.read_csv("wig20_d.csv")
```

Plik z danymi miał pierwotnie nazwę `wig20_d (1).csv`. Zmieniono ją na `wig20_d.csv`, więc skrypt działa bez zmian w kodzie. Jeśli pobierzesz dane ponownie, zapisz plik pod nazwą `wig20_d.csv`, inaczej pojawi się `FileNotFoundError`.

Format danych (ze Stooq):

```
Date,Open,High,Low,Close,Volume
04/01/2016,1832.4,1832.4,1799.78,1804.42,14419432
```

Daty mają format `DD/MM/RRRR`, dlatego w kodzie jest `dayfirst=True`. Na końcu pliku jest 34 pustych wierszy (`,,,,,`). Skrypt usuwa je w kroku czyszczenia.

### 2.3. Uruchomienie

W terminalu, **z folderu, w którym leży plik CSV**:

```bash
cd "/Users/sylwiamalinowska/Documents/Semestr III/Analiza fundamentalna i techniczna"
python3 "Analiza fundamentalna i techniczna 1.py"
```

Każdy wykres otwiera się w osobnym oknie (`plt.show()`). **Skrypt czeka, aż zamkniesz okno**, i dopiero wtedy liczy dalej.

Skrypt da się też uruchomić w Google Colab (świadczy o tym zakomentowana ścieżka `drive/MyDrive/...`). Trzeba wtedy wgrać plik CSV i ustawić do niego ścieżkę.

### 2.4. Pliki wynikowe

| Plik | Zawartość |
|---|---|
| `analiza_WIG20_2016_2026.xlsx` | wszystkie tabele wyników (12 arkuszy) |
| `01_gestosc_rozkadu_WIG20.png` | histogram, gęstość KDE i rozkład normalny |
| `02_ACF_WIG20.png` | funkcja autokorelacji |
| `03_QQ_WIG20.png` | wykres kwantyl-kwantyl |
| `04_efekt_dnia_tygodnia_WIG20.png` | średnie stopy zwrotu wg dnia tygodnia |
| `05_efekt_miesiaca_WIG20.png` | średnie stopy zwrotu wg miesiąca |

---

## 3. Parametry (sekcja 1 skryptu)

| Parametr | Wartość | Znaczenie |
|---|---|---|
| `START_DATE` | `"2016-01-01"` | początek okresu badania |
| `END_DATE` | `"2026-07-31"` | koniec okresu badania |
| `ALPHA` | `0.05` | poziom istotności testów |
| `LAGS` | `[1, 5, 10, 20, 30]` | opóźnienia w testach Ljunga-Boxa i Boxa-Pierce'a |
| `ACF_LAGS` | `40` | liczba opóźnień na wykresie ACF |
| `OUTPUT_EXCEL` | `"analiza_WIG20_2016_2026.xlsx"` | nazwa pliku wynikowego |

> **Uwaga:** tabela podsumowania (sekcja 26) ma **na sztywno wpisane** opóźnienia 1, 5, 10, 20, 30. Jeśli zmienisz `LAGS`, musisz poprawić też tę sekcję, inaczej pojawi się `KeyError`. Daty w tytule wykresu gęstości są również wpisane ręcznie.

---

## 4. Opis kolejnych kroków

### Krok 2–4: wczytanie i czyszczenie danych

1. Ujednolicenie nazw kolumn (`Date`, `Close` itd.).
2. Konwersja dat i cen. Błędne wartości zamieniane są na `NaN` (`errors="coerce"`).
3. Usunięcie wierszy bez daty lub ceny oraz cen ≤ 0.
4. Usunięcie zduplikowanych dat i sortowanie chronologiczne.
5. Zawężenie do okresu `START_DATE`–`END_DATE`.
6. **Kontrola odstępów między datami.** Skrypt pokazuje rozkład liczby dni między kolejnymi notowaniami. Typowe wartości: 1 (dzień po dniu), 3 (weekend), 4–5 (święta). Większe przerwy wskazują na braki w danych.

### Krok 5: logarytmiczne stopy zwrotu

$$
r_t = \ln\left(\frac{P_t}{P_{t-1}}\right)
$$

gdzie $P_t$ to cena zamknięcia. Pierwsza obserwacja nie ma stopy zwrotu i jest pomijana.
Logarytmiczne stopy zwrotu sumują się w czasie i mają lepsze własności statystyczne niż zwykłe stopy procentowe.

### Krok 6: statystyki opisowe

Liczba obserwacji, średnia, mediana, odchylenie standardowe, wariancja, min, max, kwartyle, **skośność** i **kurtoza**.

- `returns.kurtosis()` w pandas zwraca **kurtozę nadwyżkową** (dla rozkładu normalnego = 0). Dlatego skrypt podaje też „Kurtozę” = nadwyżkowa + 3 (dla rozkładu normalnego = 3).
- Na rynkach finansowych typowe są **grube ogony** (kurtoza > 3) i często **ujemna skośność**, czyli duże spadki zdarzają się częściej niż równie duże wzrosty.

### Krok 7: wykres gęstości (`01_...png`)

Na jednym wykresie:
- histogram stóp zwrotu (80 przedziałów, w skali gęstości),
- empiryczna gęstość **KDE** (granatowa linia),
- teoretyczny **rozkład normalny** o tej samej średniej i odchyleniu (czerwona przerywana),
- średnia (czarna kropkowana).

**Jak czytać:** jeśli KDE jest wyższe i węższe w środku niż krzywa normalna, a w ogonach leży nad nią, to rozkład jest leptokurtyczny i ma grube ogony.

### Krok 8: test Ljunga-Boxa i Boxa-Pierce'a

Sprawdzają, czy **autokorelacje do opóźnienia k są łącznie równe zero**.

- **H0:** brak autokorelacji (stopy zwrotu są niezależne w czasie)
- **H1:** występuje autokorelacja

$$
Q_{LB} = n(n+2)\sum_{k=1}^{h}\frac{\hat\rho_k^2}{n-k}, \qquad
Q_{BP} = n\sum_{k=1}^{h}\hat\rho_k^2
$$

Ljung-Box to poprawiona wersja Boxa-Pierce'a, dokładniejsza w małych próbach. Przy ok. 2600 obserwacjach wyniki obu testów będą bardzo podobne.

**Interpretacja:** p-value < 0,05 → odrzucamy H0 → przeszłe stopy zwrotu niosą informację o przyszłych, co jest argumentem przeciw słabej efektywności rynku.

### Krok 9: wykres ACF (`02_...png`)

Słupki pokazują autokorelację $\hat\rho_k$ dla opóźnień 0–40. Niebieski obszar to **95% przedział ufności** wokół zera.
Słupki wystające poza obszar oznaczają istotną autokorelację na danym opóźnieniu. Słupek dla lag = 0 zawsze wynosi 1 i nie ma znaczenia.

> Przy α = 0,05 i 40 opóźnieniach średnio ok. 2 słupki wyjdą poza przedział przypadkiem. Pojedyncze przekroczenia nie są więc dowodem na brak losowości.

### Krok 10: test serii Walda-Wolfowitza (runs test)

Bada **losowość kolejności znaków** stóp zwrotu (+/−). Stopy równe zero są pomijane.

- **H0:** znaki występują losowo
- **H1:** kolejność znaków nie jest losowa

Seria to ciąg kolejnych stóp o tym samym znaku, np. `+ + − + − − −` daje 4 serie. Przy $n_+$ dodatnich, $n_-$ ujemnych i $n = n_+ + n_-$:

$$
E(R) = 1 + \frac{2n_+n_-}{n}, \qquad
Var(R) = \frac{2n_+n_-(2n_+n_- - n)}{n^2(n-1)}, \qquad
Z = \frac{R - E(R)}{\sqrt{Var(R)}}
$$

p-value liczone jest z rozkładu normalnego (test dwustronny).

**Jak czytać Z:**
- Z < 0: **za mało serii**, czyli wzrosty i spadki „skupiają się” (trend, momentum),
- Z > 0: **za dużo serii**, czyli znaki zbyt często się zmieniają (powrót do średniej).

Test jest **nieparametryczny**: nie zakłada normalności i bada tylko znaki, nie wielkości stóp zwrotu.

### Krok 11: test Kołmogorowa-Smirnowa

Sprawdza zgodność **standaryzowanych** stóp zwrotu z rozkładem N(0,1).

- **H0:** rozkład jest normalny
- **H1:** rozkład nie jest normalny

> Skrypt sam o tym ostrzega: średnia i odchylenie są **szacowane z tej samej próby**, więc klasyczny KS jest zbyt „łagodny” (p-value zawyżone). Poprawną wersją jest **test Lillieforsa** (`statsmodels.stats.diagnostic.lilliefors`). Można też użyć testu Jarque-Bera (`scipy.stats.jarque_bera`). Jeśli KS mimo to odrzuca H0, wniosek o braku normalności jest tym mocniejszy.

### Krok 12: wykres Q-Q (`03_...png`)

Porównuje kwantyle empiryczne z kwantylami rozkładu normalnego.
- Punkty na prostej: rozkład zbliżony do normalnego.
- **Odgięcie końców w kształt litery „S”** (lewy koniec poniżej linii, prawy powyżej): **grube ogony**, typowy obraz dla stóp zwrotu.

### Krok 13: test ADF (Augmented Dickey-Fuller)

- **H0:** szereg ma pierwiastek jednostkowy (jest **niestacjonarny**)
- **H1:** szereg jest **stacjonarny**

Liczba opóźnień dobierana jest automatycznie kryterium AIC. Skrypt wypisuje statystykę, p-value i wartości krytyczne (1%, 5%, 10%).

**Interpretacja:** statystyka ADF mniejsza od wartości krytycznej (p < 0,05) → szereg stacjonarny.
Dla stóp zwrotu prawie zawsze tak jest. Ceny (poziomy indeksu) są zwykle niestacjonarne i właśnie dlatego analizuje się stopy zwrotu.

### Krok 14: zmienne kalendarzowe

Do każdej stopy zwrotu dopisywany jest dzień tygodnia (0 = poniedziałek … 4 = piątek) i miesiąc (1–12), razem z nazwami po polsku.

> Stopa zwrotu z poniedziałku obejmuje cały weekend (piątek → poniedziałek). Na tym opiera się klasyczny „efekt poniedziałku”.

### Kroki 15–20: efekt dnia tygodnia i miesiąca

Dla każdej grupy (dnia lub miesiąca) liczone są: liczba obserwacji, średnia, mediana, odchylenie, min i max. Następnie dwa testy:

| Test | H0 | Założenia |
|---|---|---|
| **ANOVA** (`f_oneway`) | średnie we wszystkich grupach są równe | normalność i równe wariancje w grupach |
| **Kruskal-Wallis** (`kruskal`) | rozkłady (mediany) we wszystkich grupach są takie same | nieparametryczny, bez założenia normalności |

Stopy zwrotu nie są normalne (patrz KS i Q-Q), dlatego **Kruskal-Wallis jest tu bardziej wiarygodny**. Skrypt wypisuje słowną interpretację tylko dla niego. Dla ANOVA podaje samo F i p-value.

### Kroki 21–23: regresje kalendarzowe z błędami HAC

Trzy modele OLS ze zmiennymi zero-jedynkowymi:

1. `Log_Return ~ C(weekday)`: dzień tygodnia, **poniedziałek = kategoria bazowa**,
2. `Log_Return ~ C(month)`: miesiąc, **styczeń = kategoria bazowa**,
3. `Log_Return ~ C(weekday) + C(month)`: oba efekty naraz.

$$
r_t = \beta_0 + \beta_1 D_{wt} + \beta_2 D_{śr} + \beta_3 D_{czw} + \beta_4 D_{pt} + \varepsilon_t
$$

**Jak czytać wyniki (`summary()`):**
- `Intercept` ($\beta_0$): średnia stopa zwrotu w kategorii bazowej (poniedziałek lub styczeń),
- `C(weekday)[T.2]` itd.: **różnica** średniej danego dnia względem poniedziałku,
- p-value współczynnika < 0,05: ten dzień lub miesiąc różni się istotnie od kategorii bazowej,
- **F-statistic** i `Prob (F-statistic)`: test łączny, czy *jakikolwiek* efekt kalendarzowy istnieje,
- R² będzie bardzo małe, co jest normalne przy dziennych stopach zwrotu.

**HAC (Newey-West, `maxlags=5`)** to błędy standardowe odporne na **heteroskedastyczność** (zmienną zmienność, np. okresy kryzysów) i **autokorelację**. Zwykłe błędy OLS byłyby w takich danych zaniżone i dawałyby fałszywie „istotne” wyniki.

### Kroki 24–25: wykresy efektów kalendarzowych (`04_`, `05_...png`)

Słupki średnich stóp zwrotu: **niebieskie** dla dodatnich, **czerwone** dla ujemnych.
Wykres nie pokazuje istotności. O istotności rozstrzygają testy z kroków 15–23.

### Krok 26: tabela podsumowująca

Zbiera statystyki i p-value wszystkich testów (17 wierszy) oraz automatyczny wniosek: „Odrzucenie H0” lub „Brak podstaw do odrzucenia H0” przy α = 0,05.

Przy testach kolumna „Statystyka” zawiera odpowiednio: Q (LB/BP), Z (runs), D (KS), τ (ADF), F (ANOVA), H (Kruskal-Wallis).

### Krok 27: eksport do Excela

| Arkusz | Zawartość |
|---|---|
| `Dane` | daty, ceny OHLC, wolumen, log-stopy zwrotu |
| `Statystyki` | statystyki opisowe |
| `Ljung_Box_Box_Pierce` | wyniki testów autokorelacji |
| `Runs_test` | test serii |
| `KS_test` | test Kołmogorowa-Smirnowa |
| `ADF` | test ADF (bez wartości krytycznych, które są tylko w konsoli) |
| `Dzien_tygodnia` | statystyki wg dnia tygodnia |
| `Miesiac` | statystyki wg miesiąca |
| `Podsumowanie` | tabela zbiorcza testów |
| `Regresja_dzien` / `Regresja_miesiac` / `Regresja_laczna` | współczynniki, błędy HAC, t, p-value |

---

## 5. Ściąga do interpretacji

| Test | p < 0,05 oznacza… | Co zwykle wychodzi dla indeksów giełdowych |
|---|---|---|
| Ljung-Box / Box-Pierce | autokorelacja, brak pełnej losowości | czasem istotne przy lag 1 lub przy dłuższych opóźnieniach |
| Runs test | kolejność znaków nielosowa | często nieistotny |
| Kołmogorow-Smirnow | rozkład nienormalny | prawie zawsze odrzucenie H0 |
| ADF | szereg stacjonarny | prawie zawsze odrzucenie H0 (stopy są stacjonarne) |
| ANOVA / Kruskal-Wallis | efekt kalendarzowy istnieje | zwykle nieistotne |
| Regresja HAC | dany dzień lub miesiąc różni się od bazowego | pojedyncze współczynniki mogą być istotne |

**Wniosek dla słabej formy efektywności rynku:** brak istotnej autokorelacji, losowa kolejność znaków i brak efektów kalendarzowych **przemawiają za** efektywnością. Istotne wyniki **przemawiają przeciw**, ale trzeba jeszcze sprawdzić, czy dałoby się na nich zarobić po kosztach transakcyjnych.

> **Problem wielokrotnego testowania:** skrypt wykonuje kilkadziesiąt testów (do tego 5 dni, 12 miesięcy i 40 lagów ACF). Przy α = 0,05 część wyników wyjdzie „istotna” czysto przypadkiem. Warto o tym wspomnieć w interpretacji.

---

## 6. Zauważone problemy i możliwe poprawki

1. **Nazwa pliku CSV**: poprawione, plik ma teraz nazwę `wig20_d.csv`.
2. **Literówka w nazwie wykresu:** `01_gestosc_rozkadu_WIG20.png` (brakuje „ł” w „rozkładu”). Działaniu to nie przeszkadza.
3. **Test KS** z parametrami szacowanymi z próby: lepiej dodać test Lillieforsa lub Jarque-Bera (patrz krok 11).
4. **Opóźnienia wpisane na sztywno** w tabeli podsumowania: przy zmianie `LAGS` trzeba je poprawić ręcznie.
5. **ANOVA** nie ma słownej interpretacji w konsoli, tylko F i p-value (wynik jest w tabeli podsumowania).
6. **`plt.show()`** wstrzymuje skrypt przy każdym wykresie. Jeśli chcesz tylko zapisać pliki PNG, zamień `plt.show()` na `plt.close()`.
7. **Pobieranie ze Stooq** (zakomentowane linie 101–105): Stooq często blokuje automatyczne pobieranie, dlatego używany jest plik lokalny.
8. W folderze są też pliki indeksów sektorowych (`wig_banki_d.csv`, `wig_budow_d.csv`, `wig_energ_d.csv`, `wig_leki_d.csv`, `wig_spozyw_d.csv`). Ten skrypt ich nie używa. Żeby przeanalizować któryś z nich, zmień nazwę pliku w linii 109 oraz nazwy WIG20 w tytułach wykresów i nazwach plików wynikowych.
