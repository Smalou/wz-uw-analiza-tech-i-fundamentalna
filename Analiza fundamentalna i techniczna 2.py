# ================================================================
# ANALIZA SEKTORÓW GPW A CYKL KONIUNKTURALNY W POLSCE
#
# Okres:
# 01.01.2016 - 31.07.2026
#
# SEKTORY:
#   WIG-BANKI
#   WIG-BUDOW
#   WIG-SPOZYW
#   WIG-TELEKOM
#   WIG-SUROWC
#
# DANE MAKRO:
#   - realny wzrost PKB
#   - inflacja HICP
#   - stopa bezrobocia
#   - stopa procentowa (jeżeli dostępna)
#
# ANALIZY:
#   - logarytmiczne stopy zwrotu
#   - agregacja miesięczna
#   - korelacje
#   - korelacje kroczące
#   - cykl koniunkturalny
#   - porównanie sektorów w fazach cyklu
#   - Kruskal-Wallis
#   - eksport Excel
#
# ================================================================


# ================================================================
# 0. INSTALACJA
# ================================================================
#
# pip install pandas numpy scipy matplotlib seaborn
# pip install requests openpyxl statsmodels
#
# ================================================================


import io
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import matplotlib.pyplot as plt
import seaborn as sns

from scipy.stats import (
    kruskal,
    f_oneway,
    pearsonr,
    spearmanr
)

import statsmodels.api as sm


warnings.filterwarnings("ignore")

sns.set_theme(
    style="whitegrid",
    context="notebook"
)


# ================================================================
# 1. PARAMETRY
# ================================================================

START = "2016-01-01"
END = "2026-07-31"

START_STOOQ = "20160101"
END_STOOQ = "20260731"

OUTPUT_DIR = Path("wyniki_WIG_sektory")
OUTPUT_DIR.mkdir(
    exist_ok=True
)

EXCEL_FILE = (
    OUTPUT_DIR /
    "WIG_sektory_cykl_koniunkturalny_2016_2026.xlsx"
)

ALPHA = 0.05

SECTORS = {
    "BANKI": "wig_banki",
    "BUDOWNICTWO": "wig_budow",
    "SPOZYWCZY": "wig_spozyw",
    "ENERGIA": "wig_energ",
    "LEKI": "wig_leki"
}


# ================================================================
# 2. FUNKCJA: POBIERANIE STOOQ
# ================================================================

def get_WIGsector_data(
    ticker
):
    #data = pd.read_csv(
    #    "drive/MyDrive/" + ticker + "_d.csv"
    #)

    data = pd.read_csv(
        ticker + "_d.csv"
    )

    data.columns = [
        c.strip().lower()
        for c in data.columns
    ]

    if "date" not in data.columns:
        raise ValueError(
            f"Brak kolumny Date dla {ticker}"
        )

    if "close" not in data.columns:
        raise ValueError(
            f"Brak kolumny Close dla {ticker}"
        )

    data["date"] = pd.to_datetime(
        data["date"],
        dayfirst=True,
        errors="coerce"
    )

    data["close"] = pd.to_numeric(
        data["close"],
        errors="coerce"
    )

    data = data[
        ["date", "close"]
    ].copy()

    data = data.dropna()

    data = data[
        data["close"] > 0
    ]

    data = (
        data
        .drop_duplicates("date")
        .sort_values("date")
        .reset_index(drop=True)
    )

    data = data[
        (data["date"] >= START)
        &
        (data["date"] <= END)
    ]

    return data


# ================================================================
# 3. POBIERANIE SEKTORÓW
# ================================================================

print("\n" + "=" * 80)
print("POBIERANIE INDEKSÓW SEKTOROWYCH GPW")
print("=" * 80)

sector_prices = {}

for sector, ticker in SECTORS.items():

    print(
        f"\nPobieranie: {sector} ({ticker})"
    )

    try:

        temp = get_WIGsector_data(
            ticker
        )

        temp = temp.rename(
            columns={
                "close": sector
            }
        )

        sector_prices[sector] = temp

        print(
            f"  obserwacje: {len(temp)}"
        )

        print(
            f"  od: {temp['date'].min().date()}"
        )

        print(
            f"  do: {temp['date'].max().date()}"
        )

    except Exception as e:

        print(
            f"  BŁĄD: {e}"
        )


# ================================================================
# 4. ŁĄCZENIE CEN SEKTOROWYCH
# ================================================================

prices = None

for sector, data in sector_prices.items():

    if prices is None:

        prices = data.copy()

    else:

        prices = prices.merge(
            data,
            on="date",
            how="outer"
        )


prices = (
    prices
    .sort_values("date")
    .reset_index(drop=True)
)


# Kontrola braków
print("\nBraki danych w cenach:")
print(
    prices.isna().sum()
)


# ================================================================
# 5. STOPY ZWROTU DZIENNE
# ================================================================

print("\n" + "=" * 80)
print("DZIENNE LOGARYTMICZNE STOPY ZWROTU")
print("=" * 80)

daily_returns = prices.copy()

for sector in SECTORS.keys():

    if sector in daily_returns.columns:

        daily_returns[sector] = np.log(
            daily_returns[sector]
            /
            daily_returns[sector].shift(1)
        )


# ================================================================
# 6. STOPY ZWROTU MIESIĘCZNE
# ================================================================
#
# Ponieważ chcemy połączyć GPW z danymi makro:
#
# dzienne ceny -> miesięczna cena końcowa
# -> miesięczna stopa logarytmiczna.
#
# ================================================================

monthly_prices = (
    prices
    .set_index("date")
    .resample("MS")
    .last()
)


monthly_returns = np.log(
    monthly_prices
    /
    monthly_prices.shift(1)
)


monthly_returns.index.name = "date"


print(
    "\nLiczba miesięcznych obserwacji:"
    f" {len(monthly_returns)}"
)


# ================================================================
# 7. FUNKCJE DO EUROSTAT
# ================================================================

EUROSTAT_BASE = (
    "https://ec.europa.eu/eurostat/api/"
    "dissemination/statistics/1.0/data/"
)


def eurostat_json(
    dataset,
    params
):

    url = (
        EUROSTAT_BASE
        + dataset
    )

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    return response.json()


# ================================================================
# 8. FUNKCJA DO ODCZYTU JSON-STAT
# ================================================================
#
# Eurostat zwraca dane w formacie JSON-stat.
# Funkcja konwertuje je do DataFrame.
#
# ================================================================

def jsonstat_to_dataframe(
    data
):

    ids = data["id"]

    sizes = data["size"]

    dimensions = data["dimension"]

    values = data["value"]

    # Kategorie każdej zmiennej
    categories = {}

    for dim in ids:

        index = (
            dimensions[dim]
            ["category"]
            ["index"]
        )

        if isinstance(index, dict):

            index = sorted(
                index,
                key=index.get
            )

        categories[dim] = [
            x
            for x in index
        ]

    # Wszystkie kombinacje
    import itertools

    rows = []

    for position, value in values.items():

        if value is None:
            continue

        # JSON-stat może używać kluczy liniowych
        position = int(position)

        coordinates = []

        remainder = position

        for size in reversed(sizes):

            coordinates.append(
                remainder % size
            )

            remainder //= size

        coordinates = list(
            reversed(coordinates)
        )

        row = {}

        for i, dim in enumerate(ids):

            row[dim] = categories[dim][
                coordinates[i]
            ]

        row["value"] = value

        rows.append(row)

    return pd.DataFrame(rows)


# ================================================================
# 9. POBRANIE PKB
# ================================================================
#
# Eurostat:
# namq_10_gdp
#
# Realny kwartalny wzrost PKB.
#
# ================================================================

print("\n" + "=" * 80)
print("POBIERANIE PKB")
print("=" * 80)

gdp_params = {
    "lang": "en",
    "geo": "PL",
    "na_item": "B1GQ",
    "unit": "CLV_PCH_PRE",
    "s_adj": "SCA",
    "freq": "Q",
    "sinceTimePeriod": "2015"
}

try:

    gdp_raw = eurostat_json(
        "namq_10_gdp",
        gdp_params
    )

    gdp = jsonstat_to_dataframe(
        gdp_raw
    )

    print(
        gdp.head()
    )

except Exception as e:

    print(
        "Błąd pobierania PKB:",
        e
    )

    gdp = pd.DataFrame()


# ================================================================
# 10. PRZYGOTOWANIE PKB
# ================================================================

if not gdp.empty:

    gdp["date"] = pd.PeriodIndex(
        gdp["time"],
        freq="Q"
    ).to_timestamp(
        how="start"
    )

    gdp["GDP_growth"] = pd.to_numeric(
        gdp["value"],
        errors="coerce"
    )

    gdp = gdp[
        ["date", "GDP_growth"]
    ].dropna()

    gdp = (
        gdp
        .sort_values("date")
        .drop_duplicates("date")
    )

else:

    gdp = pd.DataFrame(
        columns=[
            "date",
            "GDP_growth"
        ]
    )


# ================================================================
# 11. INFLACJA HICP
# ================================================================
#
# Dataset:
# prc_hicp_midx
#
# CP00 = ogólny poziom cen konsumpcyjnych.
#
# ================================================================

print("\n" + "=" * 80)
print("POBIERANIE INFLACJI HICP")
print("=" * 80)

hicp_params = {
    "lang": "en",
    "geo": "PL",
    "coicop": "CP00",
    "unit": "I15",
    "sinceTimePeriod": "2015"
}

try:

    hicp_raw = eurostat_json(
        "prc_hicp_midx",
        hicp_params
    )

    hicp = jsonstat_to_dataframe(
        hicp_raw
    )

    print(
        hicp.head()
    )

except Exception as e:

    print(
        "Błąd HICP:",
        e
    )

    hicp = pd.DataFrame()


# ================================================================
# 12. PRZYGOTOWANIE HICP
# ================================================================

if not hicp.empty:

    hicp["date"] = pd.to_datetime(
        hicp["time"]
    )

    hicp["HICP_index"] = pd.to_numeric(
        hicp["value"],
        errors="coerce"
    )

    hicp = hicp[
        ["date", "HICP_index"]
    ].dropna()

    hicp = (
        hicp
        .sort_values("date")
        .drop_duplicates("date")
    )

    # Inflacja r/r
    hicp["Inflation_YoY"] = (
        hicp["HICP_index"]
        .pct_change(12)
        * 100
    )

else:

    hicp = pd.DataFrame(
        columns=[
            "date",
            "HICP_index",
            "Inflation_YoY"
        ]
    )


# ================================================================
# 13. BEZROBOCIE
# ================================================================
#
# Eurostat:
# une_rt_m
#
# Polska, wiek 15-74, obie płcie.
#
# ================================================================

print("\n" + "=" * 80)
print("POBIERANIE STOPY BEZROBOCIA")
print("=" * 80)

unemployment_params = {
    "lang": "en",
    "geo": "PL",
    "sex": "T",
    "age": "TOTAL",
    "unit": "PC_ACT",
    "s_adj": "SA",
    "freq": "M",
    "sinceTimePeriod": "2015"
}

try:

    unemployment_raw = eurostat_json(
        "une_rt_m",
        unemployment_params
    )

    unemployment = jsonstat_to_dataframe(
        unemployment_raw
    )

    print(
        unemployment.head()
    )

except Exception as e:

    print(
        "Błąd bezrobocia:",
        e
    )

    unemployment = pd.DataFrame()


# ================================================================
# 14. PRZYGOTOWANIE BEZROBOCIA
# ================================================================

if not unemployment.empty:

    unemployment["date"] = pd.to_datetime(
        unemployment["time"]
    )

    unemployment["Unemployment"] = pd.to_numeric(
        unemployment["value"],
        errors="coerce"
    )

    unemployment = unemployment[
        ["date", "Unemployment"]
    ].dropna()

    unemployment = (
        unemployment
        .sort_values("date")
        .drop_duplicates("date")
    )

else:

    unemployment = pd.DataFrame(
        columns=[
            "date",
            "Unemployment"
        ]
    )


# ================================================================
# 15. PRZYGOTOWANIE DANYCH MAKRO
# ================================================================

print("\n" + "=" * 80)
print("ŁĄCZENIE DANYCH MAKROEKONOMICZNYCH")
print("=" * 80)

macro = pd.DataFrame(
    {
        "date": pd.date_range(
            start="2015-01-01",
            end=END,
            freq="MS"
        )
    }
)


# HICP
if not hicp.empty:

    macro = macro.merge(
        hicp[
            [
                "date",
                "Inflation_YoY"
            ]
        ],
        on="date",
        how="left"
    )


# Bezrobocie
if not unemployment.empty:

    macro = macro.merge(
        unemployment,
        on="date",
        how="left"
    )


# ================================================================
# 16. PKB KWARTALNE -> MIESIĘCZNE
# ================================================================

if not gdp.empty:

    # koniec kwartału
    gdp["quarter"] = (
        gdp["date"]
        .dt.to_period("Q")
    )

    # Mapowanie miesiąca na kwartał
    macro["quarter"] = (
        macro["date"]
        .dt.to_period("Q")
    )

    macro = macro.merge(
        gdp[
            [
                "quarter",
                "GDP_growth"
            ]
        ],
        on="quarter",
        how="left"
    )

    macro.drop(
        columns="quarter",
        inplace=True
    )

else:

    macro["GDP_growth"] = np.nan


# ================================================================
# 17. UZUPEŁNIENIE BRAKÓW MAKRO
# ================================================================

macro = (
    macro
    .sort_values("date")
    .set_index("date")
)

macro = macro.ffill()

macro = macro.reset_index()


# ================================================================
# 18. ŁĄCZENIE SEKTORÓW I MAKRO
# ================================================================

print("\n" + "=" * 80)
print("ŁĄCZENIE DANYCH SEKTOROWYCH I MAKRO")
print("=" * 80)

combined = (
    monthly_returns
    .reset_index()
    .merge(
        macro,
        on="date",
        how="left"
    )
)

combined = (
    combined
    .sort_values("date")
    .reset_index(drop=True)
)

combined = combined[
    (combined["date"] >= START)
    &
    (combined["date"] <= END)
]


# ================================================================
# 19. KONTROLA DANYCH
# ================================================================

print("\nLiczba obserwacji:")
print(
    len(combined)
)

print("\nBraki:")
print(
    combined.isna().sum()
)


# ================================================================
# 20. KORELACJE SEKTORÓW Z MAKRO
# ================================================================

macro_variables = [
    "GDP_growth",
    "Inflation_YoY",
    "Unemployment"
]

sector_names = list(
    SECTORS.keys()
)

correlation_results = []

for sector in sector_names:

    for macro_var in macro_variables:

        temp = combined[
            [
                sector,
                macro_var
            ]
        ].dropna()

        if len(temp) >= 20:

            pearson, pearson_p = pearsonr(
                temp[sector],
                temp[macro_var]
            )

            spearman, spearman_p = spearmanr(
                temp[sector],
                temp[macro_var]
            )

        else:

            pearson = np.nan
            pearson_p = np.nan
            spearman = np.nan
            spearman_p = np.nan

        correlation_results.append(
            {
                "Sektor": sector,
                "Zmienna": macro_var,
                "Pearson": pearson,
                "Pearson p-value": pearson_p,
                "Spearman": spearman,
                "Spearman p-value": spearman_p,
                "N": len(temp)
            }
        )


correlations = pd.DataFrame(
    correlation_results
)

print("\nKorelacje:")
print(
    correlations
)


# ================================================================
# 21. MACIERZ KORELACJI
# ================================================================

corr_columns = (
    sector_names
    + macro_variables
)

corr_matrix = combined[
    corr_columns
].corr(
    method="pearson"
)


plt.figure(
    figsize=(12, 9)
)

sns.heatmap(
    corr_matrix,
    annot=True,
    fmt=".2f",
    cmap="RdBu_r",
    center=0,
    square=True
)

plt.title(
    "Macierz korelacji – sektory GPW i zmienne makro"
)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "01_macierz_korelacji.png",
    dpi=300
)

plt.show()


# ================================================================
# 22. KORELACJE KROCZĄCE
# ================================================================
#
# Okna:
#   12 miesięcy
#   24 miesiące
#   36 miesięcy
#
# ================================================================

ROLLING_WINDOWS = [
    12,
    24,
    36
]

rolling_correlations = {}

for sector in sector_names:

    for macro_var in macro_variables:

        pair = combined[
            [
                sector,
                macro_var
            ]
        ]

        for window in ROLLING_WINDOWS:

            name = (
                f"{sector}_{macro_var}_"
                f"rolling_{window}"
            )

            rolling_correlations[name] = (
                pair[sector]
                .rolling(window)
                .corr(
                    pair[macro_var]
                )
            )


rolling_df = pd.DataFrame(
    rolling_correlations
    #index=combined["date"]
)

rolling_df.insert(
    0,
    "date",
    combined["date"].values
)

# ================================================================
# 23. WYKRES KORELACJI KROCZĄCEJ
# ================================================================

for macro_var in macro_variables:

    fig, axes = plt.subplots(
        len(sector_names),
        1,
        figsize=(14, 16),
        sharex=True
    )

    for ax, sector in zip(
        axes,
        sector_names
    ):

        for window in ROLLING_WINDOWS:

            column = (
                f"{sector}_{macro_var}_"
                f"rolling_{window}"
            )

            ax.plot(
                rolling_df["date"],
                rolling_df[column],
                label=f"{window}M"
            )

        ax.axhline(
            0,
            color="black",
            linewidth=0.8
        )

        ax.set_ylim(
            -1,
            1
        )

        ax.set_ylabel(
            sector
        )

        ax.legend(
            loc="upper right"
        )

    fig.suptitle(
        f"Korelacje kroczące sektorów GPW z {macro_var}",
        fontsize=15
    )

    plt.tight_layout()

    filename = (
        OUTPUT_DIR /
        f"02_rolling_{macro_var}.png"
    )

    plt.savefig(
        filename,
        dpi=300
    )

    plt.show()


# ================================================================
# 24. DEFINICJA FAZ CYKLU KONIUNKTURALNEGO
# ================================================================
#
# Używamy kwartalnego realnego wzrostu PKB.
#
# Fazy:
#
# RECESJA:
#   co najmniej dwa kolejne kwartały z ujemnym wzrostem
#   (etykietę dostają wszystkie kwartały tego okresu)
#
# SPADEK:
#   pojedynczy kwartał z ujemnym wzrostem
#   (za krótki, by uznać go za recesję)
#
# OŻYWIENIE:
#   pierwszy nieujemny kwartał po kwartale ze spadkiem PKB
#
# SPOWOLNIENIE:
#   nieujemny wzrost, ale niższy niż w poprzednim kwartale
#
# EKSPANSJA:
#   nieujemny wzrost, nie niższy niż w poprzednim kwartale
#
# Każdy kwartał należy do dokładnie jednej fazy.
# Warunki sprawdzane są w powyższej kolejności.
#
# Recesja jest ustalana ex post (patrzymy też na kolejny
# kwartał), co jest dopuszczalne w analizie historycznej.
#
# To jest operacyjna klasyfikacja badawcza, a nie oficjalne
# datowanie cyklu przez instytucję państwową.
# ================================================================

if not gdp.empty:

    cycle = gdp.copy()

    cycle = cycle.sort_values(
        "date"
    ).reset_index(drop=True)

    cycle["GDP_change"] = (
        cycle["GDP_growth"]
        .diff()
    )

    cycle["negative"] = (
        cycle["GDP_growth"] < 0
    )

    prev_negative = (
        cycle["negative"]
        .shift(1, fill_value=False)
    )

    next_negative = (
        cycle["negative"]
        .shift(-1, fill_value=False)
    )

    # Recesja:
    # ujemny kwartał sąsiadujący z innym ujemnym kwartałem
    recession_condition = (
        cycle["negative"]
        &
        (prev_negative | next_negative)
    )

    # Spadek:
    # pojedynczy ujemny kwartał
    single_drop_condition = (
        cycle["negative"]
        &
        ~recession_condition
    )

    # Ożywienie:
    # pierwszy nieujemny kwartał po spadku PKB
    recovery_condition = (
        ~cycle["negative"]
        &
        prev_negative
    )

    # Spowolnienie:
    # wzrost nieujemny, ale niższy niż kwartał wcześniej
    slowdown_condition = (
        ~cycle["negative"]
        &
        (cycle["GDP_change"] < 0)
    )

    # Ekspansja:
    # pozostałe kwartały z nieujemnym wzrostem
    cycle["phase"] = np.select(
        [
            recession_condition,
            single_drop_condition,
            recovery_condition,
            slowdown_condition
        ],
        [
            "Recesja",
            "Spadek",
            "Ożywienie",
            "Spowolnienie"
        ],
        default="Ekspansja"
    )

else:

    cycle = pd.DataFrame(
        columns=[
            "date",
            "GDP_growth",
            "phase"
        ]
    )


print("\n" + "=" * 80)
print("FAZY CYKLU KONIUNKTURALNEGO")
print("=" * 80)

print(
    cycle[
        [
            "date",
            "GDP_growth",
            "phase"
        ]
    ].to_string(index=False)
)


# ================================================================
# 25. PRZYPISANIE FAZY DO MIESIĘCY
# ================================================================

if not cycle.empty:

    cycle_monthly = (
        cycle[
            [
                "date",
                "phase"
            ]
        ]
        .copy()
    )

    cycle_monthly["date"] = (
        cycle_monthly["date"]
        .dt.to_period("Q")
    )

    combined["quarter"] = (
        combined["date"]
        .dt.to_period("Q")
    )

    combined = combined.merge(
        cycle_monthly,
        left_on="quarter",
        right_on="date",
        how="left",
        suffixes=(
            "",
            "_cycle"
        )
    )

    combined.drop(
        columns=[
            "quarter",
            "date_cycle"
        ],
        errors="ignore",
        inplace=True
    )

else:

    combined["phase"] = np.nan


# ================================================================
# 26. ŚREDNIE STOPY ZWROTU W FAZACH CYKLU
# ================================================================

phase_order = [
    "Recesja",
    "Spadek",
    "Ożywienie",
    "Ekspansja",
    "Spowolnienie"
]

phase_mean = (
    combined
    .groupby("phase")[sector_names]
    .mean()
    .reindex(phase_order)
)

phase_median = (
    combined
    .groupby("phase")[sector_names]
    .median()
    .reindex(phase_order)
)

phase_std = (
    combined
    .groupby("phase")[sector_names]
    .std()
    .reindex(phase_order)
)

phase_count = (
    combined
    .groupby("phase")[sector_names]
    .count()
    .reindex(phase_order)
)


print("\n" + "=" * 80)
print("ŚREDNIE STOPY ZWROTU W FAZACH CYKLU")
print("=" * 80)

print(
    phase_mean
)


# ================================================================
# 27. SKUMULOWANA STOPA ZWROTU W FAZACH
# ================================================================
#
# Dla każdej fazy:
#
# exp(sum(log return)) - 1
#
# ================================================================

phase_cumulative = pd.DataFrame(
    index=phase_order,
    columns=sector_names,
    dtype=float
)

for phase in phase_order:

    phase_data = combined[
        combined["phase"] == phase
    ]

    for sector in sector_names:

        values = phase_data[
            sector
        ].dropna()

        if len(values) > 0:

            phase_cumulative.loc[
                phase,
                sector
            ] = (
                np.exp(
                    values.sum()
                )
                - 1
            )


print("\nSkumulowane stopy zwrotu:")
print(
    phase_cumulative
)


# ================================================================
# 28. RANKING SEKTORÓW W FAZACH
# ================================================================

phase_ranking = {}

for phase in phase_order:

    phase_ranking[phase] = (
        phase_mean
        .loc[phase]
        .sort_values(
            ascending=False
        )
    )

print("\n" + "=" * 80)
print("RANKING SEKTORÓW")
print("=" * 80)

for phase, ranking in phase_ranking.items():

    print(
        f"\n{phase}:"
    )

    print(
        ranking
    )


# ================================================================
# 29. WYKRES ŚREDNICH STÓP ZWROTU W FAZACH
# ================================================================

phase_mean_plot = (
    phase_mean
    .T
)

phase_mean_plot.plot(
    kind="bar",
    figsize=(14, 7)
)

plt.axhline(
    0,
    color="black",
    linewidth=1
)

plt.title(
    "Średnie miesięczne stopy zwrotu sektorów "
    "w różnych fazach cyklu koniunkturalnego"
)

plt.ylabel(
    "Średnia logarytmiczna stopa zwrotu"
)

plt.xlabel(
    "Sektor"
)

plt.xticks(
    rotation=20
)

plt.legend(
    title="Faza cyklu"
)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "03_stopy_sektorow_fazy_cyklu.png",
    dpi=300
)

plt.show()


# ================================================================
# 30. HEATMAPA WYNIKÓW
# ================================================================

plt.figure(
    figsize=(12, 7)
)

sns.heatmap(
    phase_mean * 100,
    annot=True,
    fmt=".3f",
    cmap="RdYlGn",
    center=0
)

plt.title(
    "Średnia miesięczna stopa zwrotu (%) "
    "według fazy cyklu"
)

plt.xlabel(
    "Sektor"
)

plt.ylabel(
    "Faza cyklu"
)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "04_heatmap_fazy_cyklu.png",
    dpi=300
)

plt.show()


# ================================================================
# 31. TEST KRUSKALA-WALLISA
# ================================================================
#
# Dla każdego sektora:
#
# H0:
# rozkład stóp zwrotu jest taki sam
# we wszystkich fazach cyklu.
#
# ================================================================

kw_results = []

for sector in sector_names:

    groups = []

    for phase in phase_order:

        values = (
            combined.loc[
                combined["phase"] == phase,
                sector
            ]
            .dropna()
        )

        if len(values) >= 3:

            groups.append(
                values
            )

    if len(groups) >= 2:

        stat, pvalue = kruskal(
            *groups
        )

    else:

        stat = np.nan
        pvalue = np.nan

    kw_results.append(
        {
            "Sektor": sector,
            "H": stat,
            "p-value": pvalue,
            "Wniosek": (
                "Istotne różnice"
                if (
                    not pd.isna(pvalue)
                    and pvalue < ALPHA
                )
                else
                "Brak podstaw do stwierdzenia różnic"
            )
        }
    )


kw_results = pd.DataFrame(
    kw_results
)

print("\n" + "=" * 80)
print("KRUSKAL-WALLIS – SEKTORY A FAZY CYKLU")
print("=" * 80)

print(
    kw_results.to_string(
        index=False
    )
)


# ================================================================
# 32. ANOVA – DODATKOWO
# ================================================================

anova_results = []

for sector in sector_names:

    groups = []

    for phase in phase_order:

        values = (
            combined.loc[
                combined["phase"] == phase,
                sector
            ]
            .dropna()
        )

        if len(values) >= 3:

            groups.append(
                values
            )

    if len(groups) >= 2:

        stat, pvalue = f_oneway(
            *groups
        )

    else:

        stat = np.nan
        pvalue = np.nan

    anova_results.append(
        {
            "Sektor": sector,
            "F": stat,
            "p-value": pvalue
        }
    )


anova_results = pd.DataFrame(
    anova_results
)


# ================================================================
# 33. ZMIENNOŚĆ SEKTORÓW W FAZACH
# ================================================================

phase_volatility = (
    combined
    .groupby("phase")[sector_names]
    .std()
    .reindex(phase_order)
)


plt.figure(
    figsize=(14, 7)
)

sns.heatmap(
    phase_volatility * 100,
    annot=True,
    fmt=".3f",
    cmap="YlOrRd"
)

plt.title(
    "Zmienność miesięcznych stóp zwrotu "
    "sektorów według fazy cyklu"
)

plt.xlabel(
    "Sektor"
)

plt.ylabel(
    "Faza cyklu"
)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "05_zmiennosc_fazy_cyklu.png",
    dpi=300
)

plt.show()


# ================================================================
# 34. KORELACJA SEKTORÓW Z PKB
# ================================================================

gdp_correlation = []

for sector in sector_names:

    temp = combined[
        [
            sector,
            "GDP_growth"
        ]
    ].dropna()

    if len(temp) > 10:

        pearson_r, pearson_p = pearsonr(
            temp[sector],
            temp["GDP_growth"]
        )

        spearman_r, spearman_p = spearmanr(
            temp[sector],
            temp["GDP_growth"]
        )

    else:

        pearson_r = np.nan
        pearson_p = np.nan
        spearman_r = np.nan
        spearman_p = np.nan

    gdp_correlation.append(
        {
            "Sektor": sector,
            "Pearson": pearson_r,
            "Pearson p-value": pearson_p,
            "Spearman": spearman_r,
            "Spearman p-value": spearman_p,
            "N": len(temp)
        }
    )


gdp_correlation = pd.DataFrame(
    gdp_correlation
)


# ================================================================
# 35. WSPÓŁCZYNNIKI KORELACJI KROCZĄCEJ – PKB
# ================================================================

plt.figure(
    figsize=(14, 8)
)

for sector in sector_names:

    rolling = (
        combined[
            sector
        ]
        .rolling(24)
        .corr(
            combined[
                "GDP_growth"
            ]
        )
    )

    plt.plot(
        combined["date"],
        rolling,
        label=sector
    )

plt.axhline(
    0,
    color="black",
    linewidth=1
)

plt.axhline(
    0.5,
    color="grey",
    linestyle="--",
    linewidth=0.7
)

plt.axhline(
    -0.5,
    color="grey",
    linestyle="--",
    linewidth=0.7
)

plt.ylim(
    -1,
    1
)

plt.title(
    "24-miesięczna korelacja krocząca "
    "stóp zwrotu sektorów z PKB"
)

plt.ylabel(
    "Korelacja"
)

plt.xlabel(
    "Data"
)

plt.legend()

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "06_rolling_PKB_24M.png",
    dpi=300
)

plt.show()


# ================================================================
# 36. PODSUMOWANIE
# ================================================================

print("\n" + "=" * 80)
print("PODSUMOWANIE ANALIZY")
print("=" * 80)

print("\nKorelacje z PKB:")
print(
    gdp_correlation
)

print("\nKruskal-Wallis:")
print(
    kw_results
)

print("\nŚrednie stopy zwrotu:")
print(
    phase_mean
)


# ================================================================
# 37. EKSPORT DO EXCEL
# ================================================================

print("\n" + "=" * 80)
print("EKSPORT DO EXCEL")
print("=" * 80)

with pd.ExcelWriter(
    EXCEL_FILE,
    engine="openpyxl"
) as writer:

    prices.to_excel(
        writer,
        sheet_name="Ceny_sektorowe",
        index=False
    )

    daily_returns.to_excel(
        writer,
        sheet_name="Zwroty_dzienne",
        index=False
    )

    monthly_returns.to_excel(
        writer,
        sheet_name="Zwroty_miesieczne"
    )

    macro.to_excel(
        writer,
        sheet_name="Dane_makro",
        index=False
    )

    combined.to_excel(
        writer,
        sheet_name="Dane_polaczone",
        index=False
    )

    correlations.to_excel(
        writer,
        sheet_name="Korelacje",
        index=False
    )

    corr_matrix.to_excel(
        writer,
        sheet_name="Macierz_korelacji"
    )

    rolling_df.to_excel(
        writer,
        sheet_name="Korelacje_kroczace"
    )

    cycle.to_excel(
        writer,
        sheet_name="Cykl_koniunkturalny",
        index=False
    )

    phase_mean.to_excel(
        writer,
        sheet_name="Srednie_fazy"
    )

    phase_median.to_excel(
        writer,
        sheet_name="Mediany_fazy"
    )

    phase_std.to_excel(
        writer,
        sheet_name="Zmiennosc_fazy"
    )

    phase_count.to_excel(
        writer,
        sheet_name="Liczba_obserwacji_fazy"
    )

    phase_cumulative.to_excel(
        writer,
        sheet_name="Zwroty_skumulowane"
    )

    kw_results.to_excel(
        writer,
        sheet_name="Kruskal_Wallis",
        index=False
    )

    anova_results.to_excel(
        writer,
        sheet_name="ANOVA",
        index=False
    )

    gdp_correlation.to_excel(
        writer,
        sheet_name="Korelacja_PKB",
        index=False
    )


# ================================================================
# 38. ZAKOŃCZENIE
# ================================================================

print("\n" + "=" * 80)
print("ANALIZA ZAKOŃCZONA")
print("=" * 80)

print(
    f"\nPlik Excel:\n{EXCEL_FILE}"
)

print(
    f"\nWykresy zapisano w:\n{OUTPUT_DIR}"
)

print(
    "\nSektory:"
)

for sector, ticker in SECTORS.items():

    print(
        f"  {sector:20s} -> {ticker}"
    )

print(
    "\nGotowe."
)