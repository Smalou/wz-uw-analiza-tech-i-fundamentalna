# ============================================================
# EKSPORT WYNIKÓW DO DASHBOARDU
#
# Czyta pliki Excel zapisane przez:
#   - Analiza fundamentalna i techniczna 1.py  (WIG20)
#   - Analiza fundamentalna i techniczna 2.py  (sektory GPW)
# i zapisuje zbiory JSON (tablice wierszy) do dashboard/data/.
#
# Uruchom po obu skryptach analitycznych:
#   python dashboard/export_dashboard_data.py
# ============================================================

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(exist_ok=True)

WIG20_XLSX = ROOT / "analiza_WIG20_2016_2026.xlsx"
SECTORS_XLSX = (
    ROOT / "wyniki_WIG_sektory" /
    "WIG_sektory_cykl_koniunkturalny_2016_2026.xlsx"
)

ALPHA = 0.05
ACF_LAGS = 40

SECTORS = ["BANKI", "BUDOWNICTWO", "SPOZYWCZY", "ENERGIA", "LEKI"]
MACRO = ["GDP_growth", "Inflation_YoY", "Unemployment"]
PHASES = ["Spadek", "Ożywienie", "Ekspansja", "Spowolnienie"]


def clean(value):
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    if isinstance(value, (np.floating, float)):
        return None if np.isnan(value) else round(float(value), 8)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def save(name, frame):
    rows = [
        {k: clean(v) for k, v in row.items()}
        for row in frame.to_dict(orient="records")
    ]
    path = OUT / f"{name}.json"
    path.write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )
    print(f"{path.name:<28} {len(rows):>6} wierszy  {path.stat().st_size / 1024:8.1f} KB")


def verdict(p):
    return "Odrzucenie H0" if p < ALPHA else "Brak podstaw do odrzucenia H0"


# ============================================================
# 1. WIG20 – LOSOWOŚĆ I SEZONOWOŚĆ
# ============================================================

w = pd.read_excel(WIG20_XLSX, sheet_name=None)

daily = w["Dane"][["Date", "Open", "High", "Low", "Close", "Volume", "Log_Return"]]
daily.columns = ["date", "open", "high", "low", "close", "volume", "log_return"]
save("wig20_daily", daily)

stats = w["Statystyki"].rename(columns={"Unnamed: 0": "statystyka", "Wartość": "wartosc"})
save("wig20_stats", stats)

summary = w["Podsumowanie"].rename(columns={
    "Test": "test",
    "Statystyka": "statystyka",
    "p-value": "p_value",
    "Wniosek (alpha=0.05)": "wniosek",
})
groups = {
    "Ljung": "Autokorelacja",
    "Box-Pierce": "Autokorelacja",
    "Runs": "Losowość znaków",
    "Kolmogorov": "Normalność",
    "ADF": "Stacjonarność",
    "dzień": "Efekt dnia tygodnia",
    "miesiąc": "Efekt miesiąca",
}
summary["grupa"] = [
    next(g for key, g in groups.items() if key in t) for t in summary["test"]
]
save("wig20_tests", summary)

lb = w["Ljung_Box_Box_Pierce"].rename(columns={"Unnamed: 0": "lag"})
save("wig20_ljungbox", lb)

# ACF jak statsmodels.acf(alpha=0.05): przedziały Bartletta
r = daily["log_return"].dropna().to_numpy()
x = r - r.mean()
n = len(x)
denom = np.sum(x * x)
acf_vals = np.array([np.sum(x[k:] * x[:n - k]) / denom for k in range(ACF_LAGS + 1)])
var = np.ones(ACF_LAGS + 1) / n
var[0] = 0
var[2:] *= 1 + 2 * np.cumsum(acf_vals[1:-1] ** 2)
band = 1.959964 * np.sqrt(var)
acf_df = pd.DataFrame({"lag": np.arange(ACF_LAGS + 1), "acf": acf_vals, "przedzial": band})
save("wig20_acf", acf_df.iloc[1:])

weekday = w["Dzien_tygodnia"].rename(columns={"weekday_pl": "dzien"})
weekday.insert(0, "nr", range(1, len(weekday) + 1))
save("wig20_weekday", weekday)

month = w["Miesiac"].rename(columns={"Unnamed: 0": "miesiac"})
month.insert(0, "nr", range(1, len(month) + 1))
save("wig20_month", month)

weekday_names = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
month_names = month["miesiac"].tolist()


def term_label(term):
    if term == "Intercept":
        return "Stała"
    idx = int(term.split("[T.")[1].rstrip("]"))
    return weekday_names[idx] if term.startswith("C(weekday)") else month_names[idx - 1]


reg_rows = []
for sheet, model in [
    ("Regresja_dzien", "Dzień tygodnia"),
    ("Regresja_miesiac", "Miesiąc"),
    ("Regresja_laczna", "Łączna"),
]:
    reg = w[sheet].rename(columns={"Unnamed: 0": "term"})
    reg["model"] = model
    reg["zmienna"] = reg["term"].map(term_label)
    reg_rows.append(reg)
regression = pd.concat(reg_rows)[["model", "term", "zmienna", "coef", "std_err_HAC", "t", "p_value"]]
save("wig20_regression", regression)


# ============================================================
# 2. SEKTORY GPW A CYKL KONIUNKTURALNY
# ============================================================

s = pd.read_excel(SECTORS_XLSX, sheet_name=None)

save("sector_prices", s["Ceny_sektorowe"])

combined = s["Dane_polaczone"]
save("sector_monthly", combined)

matrix = s["Macierz_korelacji"].rename(columns={"Unnamed: 0": "wiersz"})
matrix_long = matrix.melt(id_vars="wiersz", var_name="kolumna", value_name="korelacja")
save("sector_corr_matrix", matrix_long)

corr = s["Korelacje"].rename(columns={
    "Sektor": "sektor",
    "Zmienna": "zmienna",
    "Pearson": "pearson",
    "Pearson p-value": "pearson_p",
    "Spearman": "spearman",
    "Spearman p-value": "spearman_p",
})
save("sector_macro_corr", corr)

cycle = s["Cykl_koniunkturalny"][["date", "quarter", "GDP_growth", "GDP_change", "phase"]]
save("business_cycle", cycle)

phase_frames = {
    "srednia": "Srednie_fazy",
    "mediana": "Mediany_fazy",
    "odchylenie": "Zmiennosc_fazy",
    "liczba_miesiecy": "Liczba_obserwacji_fazy",
    "skumulowana": "Zwroty_skumulowane",
}
phase_long = None
for col, sheet in phase_frames.items():
    frame = s[sheet].rename(columns={"Unnamed: 0": "phase"})
    frame = frame[frame["phase"].isin(PHASES)]
    frame = frame.melt(id_vars="phase", var_name="sektor", value_name=col)
    phase_long = frame if phase_long is None else phase_long.merge(frame, on=["phase", "sektor"])
save("phase_stats", phase_long)

kw = s["Kruskal_Wallis"].rename(columns={"Sektor": "sektor", "p-value": "kw_p"})
anova = s["ANOVA"].rename(columns={"Sektor": "sektor", "p-value": "anova_p"})
tests = kw[["sektor", "H", "kw_p"]].merge(anova, on="sektor")
tests["wniosek_kw"] = tests["kw_p"].map(verdict)
tests["wniosek_anova"] = tests["anova_p"].map(verdict)
save("sector_phase_tests", tests)

roll = s["Korelacje_kroczace"].drop(columns=["Unnamed: 0"])
roll_long = roll.melt(id_vars="date", var_name="seria", value_name="korelacja").dropna()
parts = roll_long["seria"].str.extract(r"^(?P<sektor>[A-Z]+)_(?P<zmienna>.+)_rolling_(?P<okno>\d+)$")
roll_long = pd.concat([roll_long[["date", "korelacja"]], parts], axis=1)
roll_long["okno"] = roll_long["okno"].astype(int)
save("rolling_corr", roll_long[["date", "sektor", "zmienna", "okno", "korelacja"]])

print("\nGotowe:", OUT)
