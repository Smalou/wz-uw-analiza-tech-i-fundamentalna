# Sektory GPW a cykl koniunkturalny w Polsce: instrukcja i objaśnienie

Plik: `Analiza fundamentalna i techniczna 2.py`

## 1. Cel skryptu

Skrypt bada, czy **stopy zwrotu indeksów sektorowych GPW** w okresie **01.01.2016–31.07.2026** są powiązane z **sytuacją makroekonomiczną w Polsce**:

1. jak sektory korelują ze **wzrostem PKB**, **inflacją** i **bezrobociem**,
2. czy te zależności są **stałe w czasie** (korelacje kroczące),
3. czy stopy zwrotu sektorów **różnią się między fazami cyklu koniunkturalnego** (Recesja, Spadek, Ożywienie, Ekspansja, Spowolnienie).

Analiza ma związek z klasyczną tezą o **rotacji sektorowej**: sektory cykliczne (banki, budownictwo) powinny zyskiwać w ożywieniu i ekspansji, a sektory defensywne (spożywczy, leki, energia) radzić sobie relatywnie lepiej w spowolnieniu i recesji.

---

## 2. Jak uruchomić

### 2.1. Środowisko

Pakiety są zainstalowane w środowisku `.venv` w tym folderze:

```bash
cd "/Users/sylwiamalinowska/Documents/Semestr III/Analiza fundamentalna i techniczna"
source .venv/bin/activate
python "Analiza fundamentalna i techniczna 2.py"
```

Na innym komputerze środowisko odtworzysz z pliku `requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.2. Potrzebne dane

| Dane | Źródło | Skąd skrypt je bierze |
|---|---|---|
| Notowania 5 indeksów sektorowych | Stooq (pliki CSV) | lokalne pliki w folderze |
| Realny wzrost PKB (kwartalny) | Eurostat `namq_10_gdp` | **pobierane z internetu** |
| Inflacja HICP | Eurostat `prc_hicp_midx` | **pobierane z internetu** |
| Stopa bezrobocia | Eurostat `une_rt_m` | **pobierane z internetu** |

Wymagane pliki CSV (nazwa = ticker + `_d.csv`):

| Sektor w skrypcie | Plik | Dane od |
|---|---|---|
| BANKI | `wig_banki_d.csv` | 2016-01-04 |
| BUDOWNICTWO | `wig_budow_d.csv` | 2016-01-04 |
| SPOZYWCZY | `wig_spozyw_d.csv` | 2016-01-04 |
| ENERGIA | `wig_energ_d.csv` | 2016-01-04 |
| LEKI | `wig_leki_d.csv` | **2017-01-02** (o rok krócej) |

> **Potrzebny jest internet.** Gdy Eurostat nie odpowie, skrypt wypisze błąd pobierania, ale będzie działał dalej z pustymi danymi makro. Korelacje i fazy cyklu wyjdą wtedy puste (NaN).

### 2.3. Wykresy a `plt.show()`

Każdy wykres otwiera się w osobnym oknie i **skrypt czeka, aż je zamkniesz**. Żeby tylko zapisać pliki bez otwierania okien, uruchom:

```bash
MPLBACKEND=Agg python "Analiza fundamentalna i techniczna 2.py"
```

### 2.4. Pliki wynikowe

Wszystko trafia do folderu **`wyniki_WIG_sektory/`**:

| Plik | Zawartość |
|---|---|
| `WIG_sektory_cykl_koniunkturalny_2016_2026.xlsx` | wszystkie tabele (17 arkuszy) |
| `01_macierz_korelacji.png` | korelacje sektorów i zmiennych makro |
| `02_rolling_GDP_growth.png` | korelacje kroczące z PKB (okna 12/24/36 mies.) |
| `02_rolling_Inflation_YoY.png` | korelacje kroczące z inflacją |
| `02_rolling_Unemployment.png` | korelacje kroczące z bezrobociem |
| `03_stopy_sektorow_fazy_cyklu.png` | średnie stopy zwrotu sektorów w fazach cyklu |
| `04_heatmap_fazy_cyklu.png` | heatmapa średnich stóp zwrotu (sektor × faza) |
| `05_zmiennosc_fazy_cyklu.png` | heatmapa zmienności (odchylenia standardowego) |
| `06_rolling_PKB_24M.png` | 24-miesięczna korelacja krocząca z PKB, wszystkie sektory |

---

## 3. Parametry (sekcja 1 skryptu)

| Parametr | Wartość | Znaczenie |
|---|---|---|
| `START`, `END` | `"2016-01-01"`, `"2026-07-31"` | okres badania |
| `START_STOOQ`, `END_STOOQ` | `"20160101"`, `"20260731"` | daty w formacie Stooq (obecnie **nieużywane**, bo dane są wczytywane z plików) |
| `OUTPUT_DIR` | `wyniki_WIG_sektory` | folder na wyniki (tworzony automatycznie) |
| `ALPHA` | `0.05` | poziom istotności |
| `SECTORS` | słownik `nazwa → ticker` | lista analizowanych sektorów |

Aby dodać lub zmienić sektor, dopisz go do słownika `SECTORS` i umieść w folderze plik `<ticker>_d.csv` pobrany ze Stooq.

---

## 4. Opis kolejnych kroków

### Kroki 2–4: wczytanie i połączenie notowań

Funkcja `get_WIGsector_data(ticker)`:
1. wczytuje plik `<ticker>_d.csv` (daty w formacie `DD/MM/RRRR`),
2. zostawia tylko kolumny `date` i `close`,
3. usuwa puste wiersze, ceny ≤ 0 i duplikaty dat, sortuje,
4. przycina dane do okresu `START`–`END`.

Następnie wszystkie sektory łączone są w jedną tabelę po dacie (`how="outer"`). Skrypt wypisuje liczbę braków: dla LEKI jest ich 251, bo indeks zaczyna się rok później.

### Krok 5: dzienne log-stopy zwrotu

$$
r_t = \ln\left(\frac{P_t}{P_{t-1}}\right)
$$

Liczone dla każdego sektora i zapisywane do Excela. Dalsza analiza używa jednak danych **miesięcznych**.

### Krok 6: miesięczne stopy zwrotu

Dane makro są miesięczne lub kwartalne, więc notowania też trzeba sprowadzić do miesięcy:

1. `resample("MS").last()`: dla każdego miesiąca bierzemy **ostatnią cenę zamknięcia** z tego miesiąca (indeks oznaczony pierwszym dniem miesiąca),
2. miesięczna stopa zwrotu = $\ln(P_{\text{koniec miesiąca}} / P_{\text{koniec poprzedniego miesiąca}})$.

Daje to 127 miesięcy (I 2016 – VII 2026). Pierwszy miesiąc nie ma stopy zwrotu, więc zostaje 126 obserwacji (dla LEKI 114).

### Kroki 7–8: pobieranie danych z Eurostatu

- `eurostat_json(dataset, params)`: wysyła zapytanie do API Eurostatu i zwraca odpowiedź w formacie **JSON-stat**.
- `jsonstat_to_dataframe(data)`: zamienia JSON-stat na tabelę pandas. JSON-stat przechowuje wartości w jednej płaskiej liście, a funkcja odtwarza z pozycji w liście współrzędne wszystkich wymiarów (kraj, jednostka, czas itd.).

### Kroki 9–14: zmienne makroekonomiczne

| Zmienna | Dataset | Parametry | Co oznacza |
|---|---|---|---|
| `GDP_growth` | `namq_10_gdp` | `B1GQ`, `CLV_PCH_PRE`, `SCA` | realny PKB, **% zmiany kwartał do kwartału**, wyrównany sezonowo i kalendarzowo |
| `Inflation_YoY` | `prc_hicp_midx` | `CP00`, `I15` | indeks HICP (2015 = 100), przeliczony na **inflację r/r** = zmiana indeksu względem tego samego miesiąca rok wcześniej, w % |
| `Unemployment` | `une_rt_m` | `TOTAL`, `PC_ACT`, `SA` | stopa bezrobocia (% aktywnych zawodowo), wyrównana sezonowo |

Dane pobierane są od 2015 r., żeby inflację r/r dało się policzyć już od stycznia 2016.

### Kroki 15–17: połączenie danych makro

1. Tworzona jest siatka miesięcy od 01.2015 do 07.2026.
2. Dołączane są inflacja i bezrobocie (miesięczne).
3. **PKB kwartalny przypisywany jest do każdego z 3 miesięcy kwartału**, np. styczeń, luty i marzec dostają wartość z I kwartału.
4. `ffill()`: brakujące wartości uzupełniane są **ostatnią znaną wartością**. Dotyczy to zwłaszcza ostatnich miesięcy, za które Eurostat jeszcze nie opublikował danych.

### Kroki 18–19: połączenie sektorów z makro

Miesięczne stopy zwrotu łączone są z danymi makro po dacie. Skrypt wypisuje liczbę obserwacji (127) i braków.

### Krok 20: korelacje sektorów ze zmiennymi makro

Dla każdej pary sektor × zmienna makro liczone są (`scipy.stats.pearsonr` i `spearmanr`):
- **korelacja Pearsona**: siła zależności liniowej,
- **korelacja Spearmana**: korelacja rang, odporna na wartości odstające i zależności nieliniowe,
- **p-value** dla obu korelacji: H0 mówi, że korelacja w populacji wynosi 0. p < 0,05 oznacza, że korelacja jest istotnie różna od zera.

Korelacja jest liczona, jeśli para ma co najmniej 20 obserwacji.

**Jak czytać:** |r| < 0,2 to bardzo słaba zależność, 0,2–0,4 słaba, 0,4–0,6 umiarkowana, > 0,6 silna.

> Dla orientacji: przy N = 126 korelacja jest istotna (α = 0,05) mniej więcej od |r| ≈ 0,175.

### Krok 21: macierz korelacji (`01_...png`)

Heatmapa korelacji Pearsona między wszystkimi sektorami i zmiennymi makro. Kolor czerwony oznacza korelację dodatnią, niebieski ujemną.
Przy okazji widać, jak mocno **sektory korelują ze sobą**. Wysoka korelacja między sektorami oznacza mniejsze korzyści z dywersyfikacji.

### Kroki 22–23: korelacje kroczące (`02_rolling_...png`)

Korelacja liczona w **przesuwającym się oknie** 12, 24 i 36 miesięcy. Pokazuje, czy zależność sektor–makro jest **stabilna**, czy zmienia się w czasie, np. odwraca się w okresie pandemii albo wysokiej inflacji w latach 2022–2023.

- Krótkie okno (12M) reaguje szybko, ale jest „poszarpane”.
- Długie okno (36M) jest gładsze, ale reaguje z opóźnieniem.
- Pierwsze 11/23/35 miesięcy nie mają wartości, bo okno jeszcze się nie wypełniło.

### Krok 24: fazy cyklu koniunkturalnego

Na podstawie **kwartalnego wzrostu PKB (k/k)** każdy kwartał dostaje dokładnie jedną fazę. Warunki sprawdzane są w tej kolejności:

| Faza | Warunek |
|---|---|
| **Recesja** | co najmniej 2 kolejne kwartały z ujemnym wzrostem PKB (etykietę dostają wszystkie kwartały tego okresu) |
| **Spadek** | pojedynczy kwartał z ujemnym wzrostem PKB |
| **Ożywienie** | pierwszy kwartał bez spadku po kwartale ze spadkiem |
| **Spowolnienie** | brak spadku, ale wzrost niższy niż kwartał wcześniej |
| **Ekspansja** | brak spadku i wzrost nie niższy niż kwartał wcześniej |

Klasyfikacja jest **operacyjna, badawcza**. Nie jest to oficjalne datowanie cyklu. Recesja wyznaczana jest *ex post*: żeby ocenić bieżący kwartał, patrzymy też na następny.

**Wynik dla Polski 2016–2026:** w tym okresie **nie było dwóch kolejnych kwartałów spadku PKB**, więc faza *Recesja* jest pusta. Pojedyncze spadki (7 kwartałów, m.in. I kw. 2016, II kw. 2020 z −9,0%, kilka kwartałów w latach 2022–2024) trafiają do fazy *Spadek*.

Liczba miesięcy w fazach (BANKI):

| Recesja | Spadek | Ożywienie | Ekspansja | Spowolnienie |
|---|---|---|---|---|
| 0 | 20 | 21 | 36 | 48 |

### Krok 25: przypisanie fazy do miesięcy

Każdy miesiąc dostaje fazę kwartału, do którego należy.

### Krok 26: średnie, mediany, odchylenia i liczebności w fazach

Statystyki miesięcznych stóp zwrotu każdego sektora w każdej fazie. Tabele są w Excelu, a średnie wypisywane też w konsoli.

### Krok 27: skumulowana stopa zwrotu w fazach

$$
R_{\text{faza}} = \exp\left(\sum r_t\right) - 1
$$

Log-stopy zwrotu można sumować, więc wynik oznacza: **ile zarobiłby inwestor, który trzymałby dany indeks tylko w miesiącach tej fazy**, a poza nimi byłby poza rynkiem.
Fazy mają różną długość, dlatego do porównań między fazami lepiej używać średnich z kroku 26.

### Krok 28: ranking sektorów w fazach

Dla każdej fazy sektory sortowane są od najwyższej do najniższej średniej stopy zwrotu. Odpowiada to na pytanie, który sektor wypadał najlepiej w danej fazie cyklu.

### Kroki 29–30: wykresy średnich (`03_`, `04_...png`)

- `03_...`: słupki średnich stóp zwrotu, osobny kolor dla każdej fazy, pogrupowane według sektorów.
- `04_...`: heatmapa sektor × faza (wartości w %). Zielony oznacza wynik dodatni, czerwony ujemny.

### Krok 31: test Kruskala-Wallisa

Dla każdego sektora osobno:
- **H0:** rozkład miesięcznych stóp zwrotu jest taki sam we wszystkich fazach cyklu,
- **H1:** przynajmniej w jednej fazie rozkład jest inny.

Test **nieparametryczny**, bez założenia normalności. Fazy z mniej niż 3 obserwacjami są pomijane, więc pusta *Recesja* nie bierze udziału w teście i porównywane są 4 fazy.

### Krok 32: ANOVA

Ten sam problem, ale test parametryczny (porównuje średnie, zakłada normalność i równe wariancje). Wyniki trafiają tylko do Excela (arkusz `ANOVA`), nie są wypisywane w konsoli.

### Krok 33: zmienność w fazach (`05_...png`)

Heatmapa odchylenia standardowego stóp zwrotu (w %) w każdej fazie. Pokazuje, czy w gorszych fazach cyklu rośnie **ryzyko** sektorów.

### Kroki 34–35: korelacja z PKB i 24-miesięczna korelacja krocząca (`06_...png`)

Ponownie korelacje Pearsona i Spearmana z PKB wraz z p-value (to te same wyniki co w kroku 20) oraz jeden wspólny wykres 24-miesięcznej korelacji kroczącej dla wszystkich sektorów. Linie przerywane na ±0,5 wyznaczają próg umiarkowanej korelacji.

### Kroki 36–37: podsumowanie i eksport do Excela

| Arkusz | Zawartość |
|---|---|
| `Ceny_sektorowe` | dzienne ceny zamknięcia |
| `Zwroty_dzienne` | dzienne log-stopy zwrotu |
| `Zwroty_miesieczne` | miesięczne log-stopy zwrotu |
| `Dane_makro` | PKB, inflacja, bezrobocie (miesięcznie) |
| `Dane_polaczone` | stopy zwrotu + makro + faza cyklu |
| `Korelacje` | Pearson i Spearman z p-value: sektor × zmienna makro |
| `Macierz_korelacji` | pełna macierz korelacji |
| `Korelacje_kroczace` | wszystkie korelacje kroczące (12/24/36M) |
| `Cykl_koniunkturalny` | kwartały, wzrost PKB, faza |
| `Srednie_fazy`, `Mediany_fazy`, `Zmiennosc_fazy`, `Liczba_obserwacji_fazy` | statystyki w fazach |
| `Zwroty_skumulowane` | skumulowane stopy zwrotu w fazach |
| `Kruskal_Wallis`, `ANOVA` | wyniki testów |
| `Korelacja_PKB` | korelacje sektorów z PKB z p-value |

---

## 5. Najważniejsze wyniki (ostatnie uruchomienie)

**Korelacja z PKB:** wszystkie słabe i ujemne.

| Sektor | Pearson | p-value | Spearman | p-value |
|---|---|---|---|---|
| BANKI | −0,05 | 0,565 | −0,04 | 0,624 |
| **BUDOWNICTWO** | **−0,27** | **0,002** | **−0,23** | **0,009** |
| SPOZYWCZY | −0,11 | 0,207 | −0,03 | 0,773 |
| ENERGIA | **−0,22** | **0,012** | −0,12 | 0,181 |
| LEKI | −0,09 | 0,322 | 0,00 | 0,968 |

Istotna jest tylko korelacja BUDOWNICTWA (w obu miarach) i ENERGII (tylko w korelacji Pearsona, więc wynik może zależeć od kilku skrajnych miesięcy, np. z 2020 r.). Żadna korelacja z inflacją ani bezrobociem nie jest istotna przy α = 0,05.

**Różnice między fazami cyklu:**

| Sektor | Kruskal-Wallis p | ANOVA p | Wniosek (α = 0,05) |
|---|---|---|---|
| BANKI | 0,156 | 0,406 | brak różnic |
| BUDOWNICTWO | 0,220 | 0,130 | brak różnic |
| SPOZYWCZY | 0,977 | 0,939 | brak różnic |
| **ENERGIA** | **0,037** | **0,048** | **istotne różnice** |
| LEKI | 0,838 | 0,711 | brak różnic |

**Interpretacja:**
- Ujemna korelacja z bieżącym PKB jest zgodna z tym, że **giełda wyprzedza gospodarkę**: rynek reaguje na oczekiwania, zanim dane o PKB zostaną opublikowane. Ceny spadają przed spowolnieniem i rosną przed ożywieniem.
- W fazie *Spadek* średnie stopy zwrotu są najwyższe (np. ENERGIA 4,5%, BUDOWNICTWO 4,1% miesięcznie). To głównie efekt **II kw. 2020 r.**: PKB spadał przez lockdown, a giełda mocno odbijała po krachu z marca. Faza obejmuje tylko 20 miesięcy, więc pojedynczy taki okres mocno wpływa na jej średnią.
- Tylko ENERGIA wykazuje istotne różnice między fazami, i to na granicy istotności. Przy 5 sektorach × 2 testach jeden taki wynik może pojawić się przypadkiem (problem wielokrotnego testowania).

---

## 6. Ograniczenia metody (warto wspomnieć w pracy)

1. **Brak opóźnień.** Stopy zwrotu porównywane są z PKB z *tego samego* kwartału, a rynek wyprzedza dane makro o kilka miesięcy. Można dodać opóźnione lub wyprzedzające zmienne, np. `combined["GDP_growth"].shift(-3)`.
2. **PKB powielony na 3 miesiące.** Korelacje z PKB liczone są na 126 obserwacjach, ale niezależnych wartości PKB jest tylko ok. 42. Rzeczywista liczba niezależnych obserwacji jest więc dużo mniejsza.
3. **Wzrost k/k jest „poszarpany”.** Fazy często zmieniają się co kwartał (np. Ekspansja → Spowolnienie → Ekspansja). Wygładzenie (średnia z 4 kwartałów albo wzrost r/r) dałoby stabilniejsze fazy.
4. **Brak recesji w próbie.** Nie da się zbadać zachowania sektorów w recesji w rozumieniu definicji „dwóch kwartałów spadku”.
5. **Uzupełnianie ostatnią wartością (`ffill`)** na końcu próby: np. inflacja za V–VII 2026 jest kopią wartości z IV 2026 (2,52%), bo nowszych danych nie było.

---

## 7. Zauważone problemy w kodzie

1. **Nagłówek pliku jest nieaktualny:** wymienia WIG-TELEKOM i WIG-SUROWC oraz stopę procentową, a skrypt analizuje ENERGIA i LEKI i nie pobiera stopy procentowej.
2. **Oś X na wykresach `02_rolling_*.png`**: poprawione, zamiast numerów wierszy są teraz daty.
3. **Nieużywane importy i parametry:** `io`, `json`, `statsmodels.api as sm`, `START_STOOQ`, `END_STOOQ`. Nie przeszkadzają w działaniu.
4. **Korelacje bez p-value**: poprawione, arkusze `Korelacje` i `Korelacja_PKB` mają teraz kolumny `Pearson p-value` i `Spearman p-value`.
5. **ANOVA** nie jest wypisywana w konsoli, jest tylko w Excelu.
