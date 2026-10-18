# ============================================================
# ANALIZA LOSOWOŚCI I SEZONOWOŚCI STÓP ZWROTU WIG20
#
# Okres:
# 01.01.2016 - 31.07.2026
#
# Źródło:
# Stooq
#
# Analizy:
# 1. Pobranie cen zamknięcia
# 2. Czyszczenie danych
# 3. Logarytmiczne stopy zwrotu
# 4. Statystyki opisowe
# 5. Histogram + funkcja gęstości
# 6. Ljung-Box
# 7. Box-Pierce
# 8. ACF
# 9. Runs test Walda-Wolfowitza
# 10. Test Kołmogorowa-Smirnowa
# 11. Q-Q plot
# 12. Test ADF
# 13. Efekt dnia tygodnia
# 14. Efekt miesiąca roku
# 15. ANOVA
# 16. Kruskal-Wallis
# 17. Regresja kalendarzowa z HAC
# 18. Eksport wyników do Excel
# ============================================================


# ============================================================
# 0. IMPORT BIBLIOTEK
# ============================================================

import io
import warnings

import requests
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import openpyxl

from scipy import stats
from scipy.stats import (
    norm,
    kstest,
    kruskal,
    f_oneway
)

from statsmodels.tsa.stattools import (
    adfuller,
    acf
)

from statsmodels.stats.diagnostic import (
    acorr_ljungbox
)

import statsmodels.formula.api as smf


warnings.filterwarnings("ignore")

sns.set_theme(
    style="whitegrid",
    context="notebook"
)


# ============================================================
# 1. PARAMETRY BADANIA
# ============================================================

START_DATE = "2016-01-01"
END_DATE = "2026-07-31"

ALPHA = 0.05

# Opóźnienia dla testów autokorelacji
LAGS = [1, 5, 10, 20, 30]

# Liczba opóźnień na wykresie ACF
ACF_LAGS = 40

# Nazwa pliku wynikowego
OUTPUT_EXCEL = "analiza_WIG20_2016_2026.xlsx"


# ============================================================
# 2. POBRANIE DANYCH ZE STOOQ
# ============================================================

print("=" * 70)
print("POBIERANIE DANYCH WIG20 ZE STOOQ")
print("=" * 70)

#url = ("https://stooq.com/q/d/l/?s=wig20&f=20160101&t=20260917&i=d")
#headers = {"User-Agent": "Chrome/81.0.4044.129"}
#response = requests.get(url,headers=headers,timeout=30)
#response.raise_for_status()
#df = pd.read_csv(io.StringIO(response.text))

#df = pd.read_csv('drive/MyDrive/wig20_d.csv')

df = pd.read_csv("wig20_d.csv")

print("\nKolumny pobranych danych:")
print(df.columns.tolist())

print("\nPierwsze obserwacje:")
print(df.head())


# ============================================================
# 3. CZYSZCZENIE DANYCH
# ============================================================

print("\n" + "=" * 70)
print("CZYSZCZENIE DANYCH")
print("=" * 70)

# Ujednolicenie nazw kolumn
df.columns = [
    col.strip().capitalize()
    for col in df.columns
]

# Konwersja daty
df["Date"] = pd.to_datetime(
    df["Date"],
    #format="yyyy-mm-dd",
    dayfirst=True,
    errors="coerce"
)

# Konwersja ceny zamknięcia
df["Close"] = pd.to_numeric(
    df["Close"],
    errors="coerce"
)

# Usunięcie błędnych dat i cen
df = df.dropna(
    subset=["Date", "Close"]
)

# Usunięcie cen <= 0
df = df[df["Close"] > 0]

# Usunięcie duplikatów dat
df = (
    df
    .drop_duplicates(subset="Date")
    .sort_values("Date")
    .reset_index(drop=True)
)

# Ponowne ograniczenie zakresu
df = df[
    (df["Date"] >= START_DATE) &
    (df["Date"] <= END_DATE)
].copy()

# Kontrola braków
missing_dates = df["Date"].isna().sum()
missing_close = df["Close"].isna().sum()

print(f"Liczba obserwacji cen: {len(df)}")
print(f"Pierwsza data:         {df['Date'].min().date()}")
print(f"Ostatnia data:         {df['Date'].max().date()}")
print(f"Brakujące daty:        {missing_dates}")
print(f"Brakujące ceny:        {missing_close}")
print(f"Duplikaty dat:         {df['Date'].duplicated().sum()}")

print("\nStatystyki cen zamknięcia:")
print(df["Close"].describe())


# ============================================================
# 4. KONTROLA KOLEJNOŚCI DAT
# ============================================================

df["date_diff"] = df["Date"].diff().dt.days

print("\nRozkład różnic pomiędzy kolejnymi datami:")
print(df["date_diff"].value_counts().sort_index())

# Kolumna pomocnicza nie będzie dalej potrzebna
df.drop(columns=["date_diff"], inplace=True)


# ============================================================
# 5. LOGARYTMICZNE STOPY ZWROTU
# ============================================================

print("\n" + "=" * 70)
print("OBLICZANIE LOGARYTMICZNYCH STÓP ZWROTU")
print("=" * 70)

df["Log_Return"] = np.log(
    df["Close"] / df["Close"].shift(1)
)

# Pierwsza obserwacja nie posiada stopy zwrotu
returns = (
    df["Log_Return"]
    .dropna()
    .copy()
)

returns.name = "Log_Return"

print(f"Liczba stóp zwrotu: {len(returns)}")


# ============================================================
# 6. STATYSTYKI OPISOWE
# ============================================================

print("\n" + "=" * 70)
print("STATYSTYKI OPISOWE STÓP ZWROTU")
print("=" * 70)

descriptive = pd.Series({
    "Liczba obserwacji": len(returns),
    "Średnia": returns.mean(),
    "Mediana": returns.median(),
    "Odchylenie standardowe": returns.std(),
    "Wariancja": returns.var(),
    "Minimum": returns.min(),
    "Maksimum": returns.max(),
    "Kwartyl 1": returns.quantile(0.25),
    "Kwartyl 3": returns.quantile(0.75),
    "Skośność": returns.skew(),
    "Kurtoza nadwyżkowa": returns.kurtosis(),
    "Kurtoza": returns.kurtosis() + 3
})

print(
    descriptive.to_string()
)


# ============================================================
# 7. FUNKCJA GĘSTOŚCI ROZKŁADU
# ============================================================

print("\n" + "=" * 70)
print("WYKRES GĘSTOŚCI ROZKŁADU")
print("=" * 70)

plt.figure(
    figsize=(13, 7)
)

sns.histplot(
    returns,
    bins=80,
    stat="density",
    color="steelblue",
    alpha=0.45,
    edgecolor=None,
    label="Histogram"
)

sns.kdeplot(
    returns,
    color="darkblue",
    linewidth=2,
    label="Empiryczna funkcja gęstości KDE"
)

# Normalny rozkład referencyjny
x = np.linspace(
    returns.min(),
    returns.max(),
    1000
)

normal_density = norm.pdf(
    x,
    loc=returns.mean(),
    scale=returns.std()
)

plt.plot(
    x,
    normal_density,
    color="red",
    linestyle="--",
    linewidth=2,
    label="Rozkład normalny"
)

plt.axvline(
    returns.mean(),
    color="black",
    linestyle=":",
    label="Średnia"
)

plt.title(
    "Rozkład dziennych logarytmicznych stóp zwrotu WIG20\n"
    "01.01.2016–31.07.2026"
)

plt.xlabel("Logarytmiczna stopa zwrotu")
plt.ylabel("Gęstość")

plt.legend()

plt.tight_layout()

plt.savefig(
    "01_gestosc_rozkadu_WIG20.png",
    dpi=300
)

plt.show()


# ============================================================
# 8. TEST LJUNGA-BOXA I BOXA-PIERCE'A
# ============================================================

print("\n" + "=" * 70)
print("TESTY LJUNGA-BOXA I BOXA-PIERCE'A")
print("=" * 70)

lb_bp = acorr_ljungbox(
    returns,
    lags=LAGS,
    boxpierce=True,
    return_df=True
)

print("\nWyniki:")
print(lb_bp)


# Interpretacja
for lag, row in lb_bp.iterrows():

    print(f"\nLag = {lag}")

    print(
        f"Ljung-Box: "
        f"stat={row['lb_stat']:.4f}, "
        f"p={row['lb_pvalue']:.6f}"
    )

    print(
        f"Box-Pierce: "
        f"stat={row['bp_stat']:.4f}, "
        f"p={row['bp_pvalue']:.6f}"
    )

    if row["lb_pvalue"] < ALPHA:
        print(
            "Ljung-Box: ODRZUCAMY H0 "
            "-> występuje autokorelacja."
        )
    else:
        print(
            "Ljung-Box: NIE ODRZUCAMY H0 "
            "-> brak podstaw do stwierdzenia autokorelacji."
        )


# ============================================================
# 9. WYKRES ACF
# ============================================================

print("\n" + "=" * 70)
print("WYKRES ACF")
print("=" * 70)

acf_values, confint = acf(
    returns,
    nlags=ACF_LAGS,
    alpha=ALPHA,
    fft=True
)

lags_acf = np.arange(
    len(acf_values)
)

plt.figure(
    figsize=(14, 7)
)

plt.stem(
    lags_acf,
    acf_values,
    basefmt=" "
)

# Przedziały ufności
plt.fill_between(
    lags_acf,
    confint[:, 0] - acf_values,
    confint[:, 1] - acf_values,
    color="lightblue",
    alpha=0.5
)

plt.axhline(
    0,
    color="black",
    linewidth=1
)

plt.title(
    "Funkcja autokorelacji (ACF) – dzienne stopy zwrotu WIG20"
)

plt.xlabel("Opóźnienie (lag)")
plt.ylabel("Autokorelacja")

plt.tight_layout()

plt.savefig(
    "02_ACF_WIG20.png",
    dpi=300
)

plt.show()


# ============================================================
# 10. TEST SERII WALDA-WOLFOWITZA
# ============================================================
#
# Testujemy losowość kolejności znaków stóp zwrotu.
#
# H0:
# znaki dodatnich i ujemnych stóp zwrotu występują losowo.
#
# H1:
# kolejność znaków nie jest losowa.
#
# Stopy zwrotu równe dokładnie zero są pomijane.
# ============================================================

print("\n" + "=" * 70)
print("TEST SERII WALDA-WOLFOWITZA")
print("=" * 70)

run_returns = returns[
    returns != 0
]

signs = np.where(
    run_returns > 0,
    1,
    -1
)

n = len(signs)

n_positive = np.sum(signs == 1)
n_negative = np.sum(signs == -1)

# Liczba serii
runs = (
    1
    + np.sum(
        signs[1:] != signs[:-1]
    )
)

# Oczekiwana liczba serii
expected_runs = (
    1
    + (
        2
        * n_positive
        * n_negative
        / n
    )
)

# Wariancja liczby serii
variance_runs = (
    2
    * n_positive
    * n_negative
    * (
        2
        * n_positive
        * n_negative
        - n
    )
    /
    (
        n**2
        * (n - 1)
    )
)

std_runs = np.sqrt(
    variance_runs
)

z_runs = (
    runs - expected_runs
) / std_runs

p_runs = (
    2
    * (
        1
        - norm.cdf(
            abs(z_runs)
        )
    )
)

runs_result = pd.Series({
    "Liczba obserwacji": n,
    "Stopy dodatnie": n_positive,
    "Stopy ujemne": n_negative,
    "Liczba serii": runs,
    "Oczekiwana liczba serii": expected_runs,
    "Odchylenie standardowe liczby serii": std_runs,
    "Statystyka Z": z_runs,
    "p-value": p_runs
})

print(
    runs_result.to_string()
)

if p_runs < ALPHA:
    print(
        "\nWYNIK: ODRZUCAMY H0."
        "\nKolejność znaków stóp zwrotu "
        "nie jest losowa."
    )
else:
    print(
        "\nWYNIK: NIE ODRZUCAMY H0."
        "\nBrak podstaw do stwierdzenia, "
        "że kolejność znaków stóp zwrotu "
        "jest nielosowa."
    )


# ============================================================
# 11. TEST KOŁMOGOROWA-SMIRNOWA
# ============================================================
#
# Sprawdzamy zgodność stóp zwrotu z rozkładem normalnym.
#
# UWAGA:
# Parametry rozkładu normalnego są estymowane z próby.
# Dlatego klasyczny KS nie jest idealnym testem normalności.
# Wynik należy traktować jako dodatkową diagnostykę,
# razem z Q-Q plotem i statystykami skośności/kurtozy.
# ============================================================

print("\n" + "=" * 70)
print("TEST KOŁMOGOROWA-SMIRNOWA")
print("=" * 70)

mean_return = returns.mean()
std_return = returns.std(
    ddof=1
)

standardized_returns = (
    returns - mean_return
) / std_return

ks_stat, ks_pvalue = kstest(
    standardized_returns,
    "norm"
)

ks_result = pd.Series({
    "Statystyka KS": ks_stat,
    "p-value": ks_pvalue
})

print(
    ks_result.to_string()
)

if ks_pvalue < ALPHA:
    print(
        "\nODRZUCAMY H0."
        "\nRozkład stóp zwrotu różni się "
        "statystycznie od rozkładu normalnego."
    )
else:
    print(
        "\nNIE ODRZUCAMY H0."
        "\nBrak podstaw do odrzucenia zgodności "
        "z rozkładem normalnym."
    )


# ============================================================
# 12. WYKRES Q-Q
# ============================================================

print("\n" + "=" * 70)
print("WYKRES Q-Q")
print("=" * 70)

plt.figure(
    figsize=(9, 9)
)

stats.probplot(
    returns,
    dist="norm",
    plot=plt
)

plt.title(
    "Wykres Q-Q – stopy zwrotu WIG20"
)

plt.xlabel(
    "Kwantyle teoretyczne rozkładu normalnego"
)

plt.ylabel(
    "Kwantyle empiryczne"
)

plt.tight_layout()

plt.savefig(
    "03_QQ_WIG20.png",
    dpi=300
)

plt.show()


# ============================================================
# 13. TEST ADF
# ============================================================
#
# H0: szereg posiada pierwiastek jednostkowy
# H1: szereg jest stacjonarny
# ============================================================

print("\n" + "=" * 70)
print("TEST ADF – AUGMENTED DICKEY-FULLER")
print("=" * 70)

adf_result = adfuller(
    returns,
    autolag="AIC"
)

adf_statistic = adf_result[0]
adf_pvalue = adf_result[1]
adf_lags = adf_result[2]
adf_nobs = adf_result[3]

adf_critical = adf_result[4]

adf_output = pd.Series({
    "Statystyka ADF": adf_statistic,
    "p-value": adf_pvalue,
    "Liczba opóźnień": adf_lags,
    "Liczba obserwacji": adf_nobs
})

print(
    adf_output.to_string()
)

print("\nWartości krytyczne:")

for key, value in adf_critical.items():
    print(
        f"{key}: {value:.6f}"
    )

if adf_pvalue < ALPHA:
    print(
        "\nODRZUCAMY H0."
        "\nStopy zwrotu są stacjonarne."
    )
else:
    print(
        "\nNIE ODRZUCAMY H0."
        "\nBrak podstaw do stwierdzenia stacjonarności."
    )


# ============================================================
# 14. PRZYGOTOWANIE ZMIENNYCH KALENDARZOWYCH
# ============================================================

analysis = df[
    ["Date", "Close", "Log_Return"]
].dropna().copy()

analysis["weekday"] = (
    analysis["Date"].dt.dayofweek
)

analysis["weekday_name"] = (
    analysis["Date"].dt.day_name()
)

analysis["month"] = (
    analysis["Date"].dt.month
)

analysis["month_name"] = (
    analysis["Date"].dt.month_name()
)


# Polskie nazwy
weekday_names_pl = {
    0: "Poniedziałek",
    1: "Wtorek",
    2: "Środa",
    3: "Czwartek",
    4: "Piątek"
}

month_names_pl = {
    1: "Styczeń",
    2: "Luty",
    3: "Marzec",
    4: "Kwiecień",
    5: "Maj",
    6: "Czerwiec",
    7: "Lipiec",
    8: "Sierpień",
    9: "Wrzesień",
    10: "Październik",
    11: "Listopad",
    12: "Grudzień"
}

analysis["weekday_pl"] = (
    analysis["weekday"]
    .map(weekday_names_pl)
)

analysis["month_pl"] = (
    analysis["month"]
    .map(month_names_pl)
)


# ============================================================
# 15. STATYSTYKI WEDŁUG DNIA TYGODNIA
# ============================================================

print("\n" + "=" * 70)
print("EFEKT DNIA TYGODNIA")
print("=" * 70)

weekday_order = [
    "Poniedziałek",
    "Wtorek",
    "Środa",
    "Czwartek",
    "Piątek"
]

weekday_stats = (
    analysis
    .groupby("weekday_pl")["Log_Return"]
    .agg(
        liczba="count",
        średnia="mean",
        mediana="median",
        odchylenie_std="std",
        minimum="min",
        maksimum="max"
    )
    .reindex(weekday_order)
)

print(
    weekday_stats.to_string()
)


# ============================================================
# 16. ANOVA – DZIEŃ TYGODNIA
# ============================================================

weekday_groups = [
    analysis.loc[
        analysis["weekday_pl"] == day,
        "Log_Return"
    ].values
    for day in weekday_order
]

anova_weekday = f_oneway(
    *weekday_groups
)

print("\nANOVA – dzień tygodnia")
print(
    f"F = {anova_weekday.statistic:.6f}"
)

print(
    f"p-value = {anova_weekday.pvalue:.6f}"
)


# ============================================================
# 17. KRUSKAL-WALLIS – DZIEŃ TYGODNIA
# ============================================================

kw_weekday = kruskal(
    *weekday_groups
)

print("\nKruskal-Wallis – dzień tygodnia")

print(
    f"H = {kw_weekday.statistic:.6f}"
)

print(
    f"p-value = {kw_weekday.pvalue:.6f}"
)

if kw_weekday.pvalue < ALPHA:
    print(
        "ODRZUCAMY H0 – dzień tygodnia "
        "ma statystycznie istotny związek "
        "ze stopami zwrotu."
    )
else:
    print(
        "NIE ODRZUCAMY H0 – brak podstaw "
        "do stwierdzenia efektu dnia tygodnia."
    )


# ============================================================
# 18. STATYSTYKI WEDŁUG MIESIĄCA
# ============================================================

print("\n" + "=" * 70)
print("EFEKT MIESIĄCA ROKU")
print("=" * 70)

month_order = list(range(1, 13))

month_stats = (
    analysis
    .groupby("month")["Log_Return"]
    .agg(
        liczba="count",
        średnia="mean",
        mediana="median",
        odchylenie_std="std",
        minimum="min",
        maksimum="max"
    )
    .reindex(month_order)
)

month_stats.index = [
    month_names_pl[m]
    for m in month_stats.index
]

print(
    month_stats.to_string()
)


# ============================================================
# 19. ANOVA – MIESIĄC
# ============================================================

month_groups = [
    analysis.loc[
        analysis["month"] == month,
        "Log_Return"
    ].values
    for month in month_order
]

anova_month = f_oneway(
    *month_groups
)

print("\nANOVA – miesiąc roku")

print(
    f"F = {anova_month.statistic:.6f}"
)

print(
    f"p-value = {anova_month.pvalue:.6f}"
)


# ============================================================
# 20. KRUSKAL-WALLIS – MIESIĄC
# ============================================================

kw_month = kruskal(
    *month_groups
)

print("\nKruskal-Wallis – miesiąc roku")

print(
    f"H = {kw_month.statistic:.6f}"
)

print(
    f"p-value = {kw_month.pvalue:.6f}"
)

if kw_month.pvalue < ALPHA:
    print(
        "ODRZUCAMY H0 – miesiąc roku "
        "ma statystycznie istotny związek "
        "ze stopami zwrotu."
    )
else:
    print(
        "NIE ODRZUCAMY H0 – brak podstaw "
        "do stwierdzenia efektu miesiąca."
    )


# ============================================================
# 21. REGRESJA – DZIEŃ TYGODNIA
# ============================================================
#
# Efekty kalendarzowe:
#
# Return_t = beta_0 + beta_1 D2 + ... + beta_4 D5 + e_t
#
# Poniedziałek jest kategorią referencyjną.
#
# Covariance type HAC = odporność na:
# - autokorelację,
# - heteroskedastyczność.
# ============================================================

print("\n" + "=" * 70)
print("REGRESJA – EFEKT DNIA TYGODNIA")
print("=" * 70)

model_weekday = smf.ols(
    "Log_Return ~ C(weekday)",
    data=analysis
).fit(
    cov_type="HAC",
    cov_kwds={"maxlags": 5}
)

print(
    model_weekday.summary()
)


# ============================================================
# 22. REGRESJA – MIESIĄC
# ============================================================

print("\n" + "=" * 70)
print("REGRESJA – EFEKT MIESIĄCA")
print("=" * 70)

model_month = smf.ols(
    "Log_Return ~ C(month)",
    data=analysis
).fit(
    cov_type="HAC",
    cov_kwds={"maxlags": 5}
)

print(
    model_month.summary()
)


# ============================================================
# 23. REGRESJA ŁĄCZNA
# ============================================================

print("\n" + "=" * 70)
print("REGRESJA ŁĄCZNA – DZIEŃ + MIESIĄC")
print("=" * 70)

model_combined = smf.ols(
    "Log_Return ~ C(weekday) + C(month)",
    data=analysis
).fit(
    cov_type="HAC",
    cov_kwds={"maxlags": 5}
)

print(
    model_combined.summary()
)


# ============================================================
# 24. WYKRES ŚREDNICH STÓP ZWROTU WG DNIA TYGODNIA
# ============================================================

plt.figure(
    figsize=(11, 6)
)

weekday_plot = (
    analysis
    .groupby("weekday_pl")["Log_Return"]
    .mean()
    .reindex(weekday_order)
)

colors = [
    "steelblue"
    if value >= 0
    else "indianred"
    for value in weekday_plot
]

plt.bar(
    weekday_plot.index,
    weekday_plot.values,
    color=colors
)

plt.axhline(
    0,
    color="black",
    linewidth=1
)

plt.title(
    "Średnie dzienne logarytmiczne stopy zwrotu WIG20\n"
    "według dnia tygodnia"
)

plt.ylabel(
    "Średnia stopa zwrotu"
)

plt.xticks(
    rotation=20
)

plt.tight_layout()

plt.savefig(
    "04_efekt_dnia_tygodnia_WIG20.png",
    dpi=300
)

plt.show()


# ============================================================
# 25. WYKRES ŚREDNICH STÓP ZWROTU WG MIESIĄCA
# ============================================================

month_plot = (
    analysis
    .groupby("month")["Log_Return"]
    .mean()
    .reindex(month_order)
)

month_plot.index = [
    month_names_pl[m]
    for m in month_plot.index
]

plt.figure(
    figsize=(14, 6)
)

colors = [
    "steelblue"
    if value >= 0
    else "indianred"
    for value in month_plot
]

plt.bar(
    month_plot.index,
    month_plot.values,
    color=colors
)

plt.axhline(
    0,
    color="black",
    linewidth=1
)

plt.title(
    "Średnie dzienne logarytmiczne stopy zwrotu WIG20\n"
    "według miesiąca roku"
)

plt.ylabel(
    "Średnia stopa zwrotu"
)

plt.xticks(
    rotation=35
)

plt.tight_layout()

plt.savefig(
    "05_efekt_miesiaca_WIG20.png",
    dpi=300
)

plt.show()


# ============================================================
# 26. PODSUMOWANIE WYNIKÓW TESTÓW
# ============================================================

summary = pd.DataFrame({
    "Test": [
        "Ljung-Box lag 1",
        "Ljung-Box lag 5",
        "Ljung-Box lag 10",
        "Ljung-Box lag 20",
        "Ljung-Box lag 30",
        "Box-Pierce lag 1",
        "Box-Pierce lag 5",
        "Box-Pierce lag 10",
        "Box-Pierce lag 20",
        "Box-Pierce lag 30",
        "Runs test",
        "Kolmogorov-Smirnov",
        "ADF",
        "ANOVA – dzień tygodnia",
        "Kruskal-Wallis – dzień tygodnia",
        "ANOVA – miesiąc",
        "Kruskal-Wallis – miesiąc"
    ],

    "Statystyka": [
        lb_bp.loc[1, "lb_stat"],
        lb_bp.loc[5, "lb_stat"],
        lb_bp.loc[10, "lb_stat"],
        lb_bp.loc[20, "lb_stat"],
        lb_bp.loc[30, "lb_stat"],

        lb_bp.loc[1, "bp_stat"],
        lb_bp.loc[5, "bp_stat"],
        lb_bp.loc[10, "bp_stat"],
        lb_bp.loc[20, "bp_stat"],
        lb_bp.loc[30, "bp_stat"],

        z_runs,
        ks_stat,
        adf_statistic,
        anova_weekday.statistic,
        kw_weekday.statistic,
        anova_month.statistic,
        kw_month.statistic
    ],

    "p-value": [
        lb_bp.loc[1, "lb_pvalue"],
        lb_bp.loc[5, "lb_pvalue"],
        lb_bp.loc[10, "lb_pvalue"],
        lb_bp.loc[20, "lb_pvalue"],
        lb_bp.loc[30, "lb_pvalue"],

        lb_bp.loc[1, "bp_pvalue"],
        lb_bp.loc[5, "bp_pvalue"],
        lb_bp.loc[10, "bp_pvalue"],
        lb_bp.loc[20, "bp_pvalue"],
        lb_bp.loc[30, "bp_pvalue"],

        p_runs,
        ks_pvalue,
        adf_pvalue,
        anova_weekday.pvalue,
        kw_weekday.pvalue,
        anova_month.pvalue,
        kw_month.pvalue
    ]
})

summary["Wniosek (alpha=0.05)"] = np.where(
    summary["p-value"] < ALPHA,
    "Odrzucenie H0",
    "Brak podstaw do odrzucenia H0"
)

print("\n" + "=" * 70)
print("PODSUMOWANIE TESTÓW")
print("=" * 70)

print(
    summary.to_string(index=False)
)


# ============================================================
# 27. EKSPORT DO EXCEL
# ============================================================

print("\n" + "=" * 70)
print("ZAPIS WYNIKÓW DO EXCEL")
print("=" * 70)

with pd.ExcelWriter(
    OUTPUT_EXCEL,
    engine="openpyxl"
) as writer:

    # Dane cenowe i stopy zwrotu
    df.to_excel(
        writer,
        sheet_name="Dane",
        index=False
    )

    # Statystyki opisowe
    descriptive.to_frame(
        "Wartość"
    ).to_excel(
        writer,
        sheet_name="Statystyki"
    )

    # Ljung-Box / Box-Pierce
    lb_bp.to_excel(
        writer,
        sheet_name="Ljung_Box_Box_Pierce"
    )

    # Runs test
    runs_result.to_frame(
        "Wartość"
    ).to_excel(
        writer,
        sheet_name="Runs_test"
    )

    # KS
    ks_result.to_frame(
        "Wartość"
    ).to_excel(
        writer,
        sheet_name="KS_test"
    )

    # ADF
    adf_output.to_frame(
        "Wartość"
    ).to_excel(
        writer,
        sheet_name="ADF"
    )

    # Dzień tygodnia
    weekday_stats.to_excel(
        writer,
        sheet_name="Dzien_tygodnia"
    )

    # Miesiąc
    month_stats.to_excel(
        writer,
        sheet_name="Miesiac"
    )

    # Podsumowanie
    summary.to_excel(
        writer,
        sheet_name="Podsumowanie",
        index=False
    )

    # Wyniki regresji
    regression_weekday = pd.DataFrame({
        "coef": model_weekday.params,
        "std_err_HAC": model_weekday.bse,
        "t": model_weekday.tvalues,
        "p_value": model_weekday.pvalues
    })

    regression_weekday.to_excel(
        writer,
        sheet_name="Regresja_dzien"
    )

    regression_month = pd.DataFrame({
        "coef": model_month.params,
        "std_err_HAC": model_month.bse,
        "t": model_month.tvalues,
        "p_value": model_month.pvalues
    })

    regression_month.to_excel(
        writer,
        sheet_name="Regresja_miesiac"
    )

    regression_combined = pd.DataFrame({
        "coef": model_combined.params,
        "std_err_HAC": model_combined.bse,
        "t": model_combined.tvalues,
        "p_value": model_combined.pvalues
    })

    regression_combined.to_excel(
        writer,
        sheet_name="Regresja_laczna"
    )


# ============================================================
# 28. KOŃCOWY KOMUNIKAT
# ============================================================

print("\n" + "=" * 70)
print("ANALIZA ZAKOŃCZONA")
print("=" * 70)

print(
    f"\nWyniki zapisano do pliku:"
    f"\n{OUTPUT_EXCEL}"
)

print(
    "\nWygenerowane wykresy:"
)

print(
    "01_gestosc_rozkadu_WIG20.png"
)

print(
    "02_ACF_WIG20.png"
)

print(
    "03_QQ_WIG20.png"
)

print(
    "04_efekt_dnia_tygodnia_WIG20.png"
)

print(
    "05_efekt_miesiaca_WIG20.png"
)