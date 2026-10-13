"""Beats by Dre / interactive portfolio dashboard.

Presentation artwork comes from the user-provided PDF. Summary metrics were
reproduced from the source analysis notebook and presentation; 1,300 cleaned
individual reviews are included for real, interactive drilldowns. The review
explorer also accepts a replacement CSV without changing the historical slides.
"""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Beats | Product Intelligence",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent


def find_file(filename: str, subfolder: str) -> Path:
    """Find bundled files in either nested folders OR the GitHub repo root.

    Supports both the ZIP project's `data/` / `assets/` structure and a
    flattened GitHub upload where CSV, WEBP and PDF files sit beside app.py.
    """
    relative = Path(filename)
    candidates = [
        ROOT / subfolder / relative,   # data/brand_summary.csv; assets/slides/slide_01.webp
        ROOT / relative,               # slide_01.webp under a slides/ folder, etc.
        ROOT / subfolder / relative.name,
        ROOT / relative.name,          # flattened files uploaded beside app.py
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"Missing {filename!r}. Upload it to the same GitHub folder as app.py "
        f"or the {subfolder}/ folder. Searched: "
        + ", ".join(str(p) for p in candidates)
    )


def data_file(filename: str) -> Path:
    return find_file(filename, "data")


def asset_file(filename: str) -> Path:
    return find_file(filename, "assets")
RED = "#ef101c"
RED_DARK = "#99090e"
PINK = "#f6a2a4"
WHITE = "#fff1f1"
MUTED = "#b6a7a9"
BASE = "#100b0c"


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        pd.read_csv(data_file("brand_summary.csv")),
        pd.read_csv(data_file("family_summary.csv")),
        pd.read_csv(data_file("asin_summary.csv")),
        pd.read_csv(data_file("positive_themes_presentation.csv")),
        pd.read_csv(data_file("negative_themes_presentation.csv")),
    )


def clean_reviews(raw: pd.DataFrame) -> pd.DataFrame:
    """Mirror the notebook's cleaning to preserve the 1,300-review sample."""
    raw = raw.copy()
    raw.columns = raw.columns.astype(str).str.strip()
    missing = {"brand_name", "rating"} - set(raw.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    raw["rating"] = pd.to_numeric(raw["rating"], errors="coerce")
    raw = raw.dropna(subset=["brand_name", "rating"])
    raw = raw[raw["rating"].between(1, 5)].copy()
    if {"user_name", "product_name", "review_content"}.issubset(raw.columns):
        raw = raw.drop_duplicates(
            subset=["user_name", "product_name", "review_content"], keep="first"
        ).copy()
    raw["brand_name"] = raw["brand_name"].astype(str).str.strip()
    raw["sentiment"] = raw["rating"].map(
        lambda x: "Positive" if x >= 4 else ("Low-rated" if x <= 2 else "Neutral")
    )
    if "date_of_review" in raw.columns:
        raw["date_of_review"] = pd.to_datetime(
            raw["date_of_review"], errors="coerce", format="mixed"
        )
    return raw.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_packaged_reviews() -> pd.DataFrame:
    return clean_reviews(pd.read_csv(data_file("amazon_headphone_reviews.csv"), low_memory=False))


@st.cache_data(show_spinner=False)
def data_uri(filename: str) -> str:
    # All callers use fixed, packaged artwork filenames, never untrusted input.
    payload = base64.b64encode((asset_file(filename)).read_bytes()).decode("ascii")
    return f"data:image/webp;base64,{payload}"


def section(kicker: str, title: str, description: str = "") -> None:
    st.markdown(
        f'<div class="section-label">{escape(kicker.upper())}</div>'
        f'<h2 class="section-heading">{escape(title)}</h2>'
        f'<p class="section-copy">{escape(description)}</p>',
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str, sub: str = "", accent: bool = False) -> None:
    st.markdown(
        f'<div class="kpi {"accent" if accent else ""}">'
        f'<div class="kpi-label">{escape(label)}</div>'
        f'<div class="kpi-value">{escape(str(value))}</div>'
        f'<div class="kpi-sub">{escape(sub)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def note(text: str, alert: bool = False) -> None:
    cls = "note alert" if alert else "note"
    st.markdown(f'<div class="{cls}">{escape(text)}</div>', unsafe_allow_html=True)


def artwork(filename: str, label: str, height: int = 440) -> None:
    st.markdown(
        f'<div class="artwork" style="height:{height}px;'
        f'background-image:linear-gradient(0deg,rgba(16,11,12,.6),transparent 40%),'
        f'url(\'{data_uri(filename)}\')">'
        f'<span class="artwork-label">{escape(label)}</span></div>',
        unsafe_allow_html=True,
    )


def chart_style(fig: go.Figure, height: int = 420, xgrid: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", color=WHITE, size=13),
        margin=dict(l=14, r=24, t=42, b=24),
        hoverlabel=dict(bgcolor="#271319", bordercolor=RED, font_color=WHITE),
        showlegend=False,
        dragmode=False,
        xaxis=dict(showgrid=xgrid, gridcolor="rgba(255,255,255,.09)", zeroline=False,
                   tickfont=dict(color=MUTED)),
        yaxis=dict(showgrid=not xgrid, gridcolor="rgba(255,255,255,.08)", zeroline=False,
                   tickfont=dict(color=WHITE)),
    )
    return fig


def display_chart(fig: go.Figure) -> None:
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def brand_chart(frame: pd.DataFrame, metric: str, height: int = 420) -> go.Figure:
    is_rating = metric == "Average star rating"
    value_col = "avg_rating" if is_rating else "percentage_of_low_ratings"
    ascending = is_rating  # highest rated or lowest complaint share shown on top
    part = frame.sort_values(value_col, ascending=ascending)
    colors = [RED if name == "Beats" else PINK for name in part.brand_name]
    fig = go.Figure(go.Bar(
        x=part[value_col], y=part.brand_name, orientation="h", marker_color=colors,
        marker_line_width=0, customdata=part[["reviews", "avg_rating", "percentage_of_low_ratings"]].values,
        text=[f"{v:.2f}" if is_rating else f"{v:.1f}%" for v in part[value_col]],
        textposition="outside", textfont=dict(color=WHITE, size=13),
        hovertemplate=("<b>%{y}</b><br>Average stars: %{customdata[1]:.2f} / 5"
                       "<br>Low-rated: %{customdata[2]:.1f}%"
                       "<br>Reviews: %{customdata[0]:,}<extra></extra>"),
    ))
    chart_style(fig, height)
    fig.update_layout(xaxis_title="Average star rating (out of 5)" if is_rating else "1–2 star reviews (%)", yaxis_title=None)
    fig.update_xaxes(range=[0, 5.3] if is_rating else [0, max(5, part[value_col].max() * 1.23)])
    fig.update_yaxes(automargin=True)
    return fig


def themes_chart(frame: pd.DataFrame, mode: str) -> go.Figure:
    part = frame.sort_values("percentage", ascending=True)
    color = RED if mode == "Trust-breakers" else PINK
    fig = go.Figure(go.Bar(
        x=part.percentage, y=part.theme, orientation="h", marker_color=color,
        text=[f"{v:g}%" for v in part.percentage], textposition="outside",
        textfont=dict(color=WHITE),
        hovertemplate="<b>%{y}</b><br>Share of relevant reviews: %{x:.1f}%<extra></extra>",
    ))
    chart_style(fig, 380)
    fig.update_layout(xaxis_title="Mention share (%)", yaxis_title=None)
    fig.update_xaxes(range=[0, max(45, part.percentage.max() * 1.25)])
    fig.update_yaxes(automargin=True)
    return fig


def model_comparison_chart(families: pd.DataFrame, metric: str) -> go.Figure:
    measure = "avg_rating" if metric == "Average rating" else "percent_low_ratings"
    colors = [RED if x == "Solo 4" else PINK for x in families.beats_family]
    fig = go.Figure(go.Bar(
        x=families.beats_family, y=families[measure], marker_color=colors,
        text=[f"{v:.2f}★" if metric == "Average rating" else f"{v:.1f}%" for v in families[measure]],
        textposition="outside", textfont=dict(color=WHITE, size=15),
        customdata=families[["reviews", "avg_rating", "percent_low_ratings"]].values,
        hovertemplate=("<b>%{x}</b><br>Reviews: %{customdata[0]:,}"
                       "<br>Average rating: %{customdata[1]:.2f}★"
                       "<br>Low-rated reviews: %{customdata[2]:.1f}%<extra></extra>"),
    ))
    chart_style(fig, 390, xgrid=False)
    fig.update_layout(xaxis_title=None, yaxis_title=metric)
    fig.update_yaxes(range=[0, 5.15] if metric == "Average rating" else [0, 14])
    return fig


def asin_chart(asins: pd.DataFrame, metric: str) -> go.Figure:
    measure = "avg_rating" if metric == "Average rating" else "percent_low_ratings"
    part = asins.sort_values(measure, ascending=True)
    palette = [RED if "Solo 4" in x else PINK for x in part.product_name]
    # Product names from the notebook may be shortened; ASINs are canonical identifiers.
    fig = go.Figure(go.Bar(
        y=part.product_asin, x=part[measure], orientation="h", marker_color=palette,
        customdata=part[["product_name", "reviews", "avg_rating", "percent_low_ratings"]].values,
        text=[f"{v:.2f}★" if metric == "Average rating" else f"{v:.1f}%" for v in part[measure]],
        textposition="outside", textfont=dict(color=WHITE),
        hovertemplate=("<b>%{y}</b><br>%{customdata[0]}"
                       "<br>Reviews: %{customdata[1]:,}"
                       "<br>Average: %{customdata[2]:.2f}★"
                       "<br>Low-rated: %{customdata[3]:.1f}%<extra></extra>"),
    ))
    chart_style(fig, 395)
    fig.update_layout(xaxis_title=metric, yaxis_title="Amazon listing (ASIN)")
    fig.update_xaxes(range=[0, 5.6] if metric == "Average rating" else [0, max(10, part[measure].max() * 1.23)])
    return fig


STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800;900&family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {font-family:'Inter',Arial,sans-serif;}
[data-testid="stAppViewContainer"] {background:radial-gradient(circle at 90% 0%,#25070e 0%,transparent 37%),#0d090b;color:#fff2f1;}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stSidebar"] {background:#160d10;border-right:1px solid #5c1b23;}
[data-testid="stSidebar"] * {color:#f8e8e9;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {line-height:1.4;}
[data-testid="stSidebar"] .stRadio label {font-weight:650;}
[data-testid="stSidebar"] hr {border-color:#56212a;}
[data-testid="stMainBlockContainer"] {max-width:1480px;padding-top:2rem;padding-bottom:5rem;}
.stApp h1,.stApp h2,.stApp h3 {font-family:'Barlow Condensed','Arial Narrow',Impact,sans-serif;letter-spacing:.1px;}
.stApp p,.stApp label {color:#ded0d1;}
.sidebar-brand {font-family:'Barlow Condensed',Impact,sans-serif;font-size:44px;font-weight:900;letter-spacing:-1px;line-height:.9;color:white;margin:10px 0 4px;}
.sidebar-brand span {color:#ef101c;}
.sidebar-sub {font-size:10px;letter-spacing:2.8px;color:#e78d96;margin:15px 0 29px;}
.sidebar-note {font-size:12px;color:#bda7ac;line-height:1.65;margin-top:30px;}
.tag,.section-label {font-size:11px;font-weight:800;letter-spacing:2.4px;color:#fa454d;text-transform:uppercase;}
.section-label {margin-top:22px;}
.section-heading {font-weight:900!important;font-size:clamp(37px,4vw,60px)!important;line-height:.94!important;margin:10px 0 8px!important;color:#ffeded!important;}
.section-copy {font-size:15px;color:#c3b3b6;line-height:1.65;max-width:880px;margin:10px 0 24px;}
.beats-hero {min-height:390px;border:1px solid #71202b;border-radius:14px;background-size:cover;background-position:center 43%;overflow:hidden;padding:47px 48px;position:relative;display:flex;flex-direction:column;justify-content:space-between;box-shadow:0 20px 60px #0008;}
.beats-hero h1 {font-weight:900!important;font-size:clamp(54px,5.5vw,92px)!important;line-height:.9!important;color:white!important;margin:14px 0!important;letter-spacing:-1px;max-width:880px;}
.beats-hero h1 span {color:#ff202a;}
.beats-hero p {font-size:15px;max-width:550px;line-height:1.7;color:#f9dbde;}
.hero-eyebrow {display:inline-block;font-weight:800;color:#fff;border:1px solid #d51b29;background:#200d11c9;padding:7px 12px;font-size:10px;letter-spacing:2px;}
.hero-bottom {display:inline-block;background:#96070edb;padding:9px 13px;font-size:11px;font-weight:700;color:white;letter-spacing:.4px;max-width:590px;}
.kpi {min-height:136px;background:linear-gradient(140deg,#221014,#120d0e);border:1px solid #5a222a;border-radius:12px;padding:19px 21px;margin:10px 0;}
.kpi.accent {border-top:3px solid #f01b27;}
.kpi-label {font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:#d5babe;font-weight:750;}
.kpi-value {font-family:'Barlow Condensed',Impact,sans-serif;font-weight:900;font-size:52px;line-height:1.1;color:#fff1f1;}
.kpi-sub {font-size:12px;color:#ba9fa3;}
.artwork {width:100%;background-position:center center;background-size:cover;border-radius:12px;border:1px solid #5f202a;position:relative;box-shadow:0 15px 45px #0009;}
.artwork-label {position:absolute;bottom:17px;left:16px;font-weight:800;font-size:11px;letter-spacing:2.3px;color:white;background:#a60a16dd;padding:8px 12px;}
.note {margin:17px 0 24px;padding:16px 19px;border-left:3px solid #e51623;border-radius:5px;background:#300c14;color:#f7d4d7;font-size:13px;line-height:1.6;}
.note.alert {border-left-color:#f28d96;background:#2b1719;}
.story-card {border-top:3px solid #e40b16;background:#1c1013;border-radius:5px;padding:17px 18px;margin-bottom:13px;min-height:148px;}
.story-card .num {font:900 45px 'Barlow Condensed',Impact,sans-serif;color:#e4111c;line-height:.9;}
.story-card .story-name {font:800 24px 'Barlow Condensed',Impact,sans-serif;color:white;margin:12px 0 7px;line-height:1;}
.story-card p {font-size:12px;color:#c8b4b9;line-height:1.5;margin:0;}
[data-testid="stWidgetLabel"] p {color:#f5e7e9!important;font-weight:700!important;}
[data-baseweb="select"]>div {background:#251519!important;border:1px solid #74313a!important;color:white!important;}
[data-baseweb="input"]>div {background:#251519!important;border:1px solid #74313a!important;}
.stButton button, .stDownloadButton button {color:#fff!important;background:#8c0711!important;border:1px solid #ce202a!important;font-weight:750!important;}
.stButton button:hover,.stDownloadButton button:hover {background:#b20a17!important;border-color:#f92839!important;}
[data-testid="stDataFrame"] {border:1px solid #57222a;border-radius:8px;}
[data-testid="stVerticalBlockBorderWrapper"] {background:#1b0f12;border-color:#5a2832;}
.stTabs [data-baseweb="tab-list"] {gap:12px;}
.stTabs [data-baseweb="tab"] {background:#251317;border-radius:6px;color:white;}
.stTabs [aria-selected="true"] {border-bottom:2px solid #ed1422;}
hr {border-color:#61303a!important;}
.footer {color:#947f84;font-size:11px;border-top:1px solid #462127;padding-top:15px;margin-top:42px;}
@media (max-width:760px) {.beats-hero{padding:24px;min-height:350px;background-position:61% center}.beats-hero h1{font-size:55px!important}.section-heading{font-size:39px!important}.kpi-value{font-size:43px}.artwork{height:290px!important}}
</style>
"""

st.markdown(STYLES, unsafe_allow_html=True)
brands, families, asins, positive_themes, negative_themes = load_data()

with st.sidebar:
    st.markdown('<div class="sidebar-brand">beats<span>.</span><br>INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">MARKET ANALYSIS / PRODUCT STRATEGY</div>', unsafe_allow_html=True)
    page = st.radio(
        "NAVIGATION",
        ["01  Overview", "02  Competitive position", "03  Product diagnostics",
         "04  Customer signals", "05  Launch strategy", "06  Review explorer", "07  Original slides"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown(
        '<div class="sidebar-note"><b>GRACIE SCHMIDT</b><br>'
        '8 brands · 1,300 cleaned Amazon reviews<br>'
        'Includes all 1,300 cleaned review records for live exploration.<br><br>'
        'Directional customer signals — not a total-market demand estimate.</div>',
        unsafe_allow_html=True,
    )


if page.startswith("01"):
    st.markdown(
        '<div class="beats-hero" style="background-image:'
        f'linear-gradient(90deg,rgba(13,8,10,.97) 0%,rgba(13,8,10,.82) 44%,rgba(13,8,10,.12) 100%),url(\'{data_uri("hero.webp")}\')">'
        '<div><span class="hero-eyebrow">MARKET ANALYSIS&nbsp;&nbsp; / &nbsp;&nbsp;PRODUCT STRATEGY</span>'
        '<h1>BEATS BY DRE<br><span>PRODUCT</span> INTELLIGENCE</h1>'
        '<p>From real customer feedback to a smarter premium-headphone strategy. '
        'Explore the numbers behind the original launch recommendation.</p></div>'
        '<div><span class="hero-bottom">THE ANSWER → FIX TRUST FIRST. THEN VALIDATE THE NEXT LAUNCH.</span></div>'
        '</div>', unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Analyzed reviews", f"{int(brands.reviews.sum()):,}", "Cleaned Amazon review dataset", accent=True)
    with c2: kpi("Competing brands", str(len(brands)), "Including Beats")
    with c3: kpi("Beats reviews", str(int(brands.loc[brands.brand_name == 'Beats', 'reviews'].iloc[0])), "Across 2 product families")
    with c4: kpi("Beats average rating", "4.41★", "Across 499 reviews")
    section("The competitive landscape", "STRONG BRAND. MIXED EXECUTION.",
            "Beats is competitive at the brand level, but the biggest differences emerge when we look at product families and individual listings.")
    left, right = st.columns([1.55, 1], gap="large")
    with left:
        display_chart(brand_chart(brands, "Average star rating", 460))
    with right:
        artwork("racing.webp", "COMPETITIVE POSITION / 08 BRANDS", 450)
    note("Strategic conclusion: Anchor premium positioning with Studio Pro, investigate Solo 4's risk, and concept-test a comfort-first everyday headphone before any major new launch.")
    section("The roadmap", "STABILIZE. POSITION. TEST.", "A phased recommendation, not an immediate launch approval.")
    steps = [
        ("01", "Diagnose Solo 4", "Review reliability, comfort, fulfillment and listing variation."),
        ("02", "Strengthen Studio Pro", "Build the premium story around a stronger product family."),
        ("03", "Concept-test", "Test comfort-first everyday audio with target customers."),
        ("04", "Prove the economics", "Estimate demand, margin, costs and launch gates."),
    ]
    columns = st.columns(4)
    for col, (number, name, desc) in zip(columns, steps):
        with col:
            st.markdown(f'<div class="story-card"><div class="num">{number}</div>'
                        f'<div class="story-name">{escape(name)}</div><p>{escape(desc)}</p></div>',
                        unsafe_allow_html=True)

elif page.startswith("02"):
    section("Competitive position", "BEATS IS COMPETITIVE, NOT CLEARLY LEADING.",
            "Filter brands and switch the comparison metric. Every value comes from the saved analysis notebook.")
    selection, control = st.columns([2.3, 1.2])
    with selection:
        chosen = st.multiselect("Brands to display", brands.brand_name.tolist(), default=brands.brand_name.tolist())
    with control:
        metric = st.radio("Compare", ["Average star rating", "Low rating %"], horizontal=True)
    if chosen:
        display_chart(brand_chart(brands[brands.brand_name.isin(chosen)], metric, 510))
    else:
        st.info("Select at least one brand to display a comparison.")
    c1, c2 = st.columns([1.2, 1], gap="large")
    with c1:
        selected_brand = st.selectbox("Inspect a brand", brands.brand_name.tolist(), index=brands.brand_name.tolist().index("Beats"))
        brand = brands.loc[brands.brand_name == selected_brand].iloc[0]
        b1, b2, b3 = st.columns(3)
        with b1: kpi("Reviews", str(int(brand.reviews)))
        with b2: kpi("Avg. rating", f"{brand.avg_rating:.2f}★")
        with b3: kpi("Low-rated", f"{brand.percentage_of_low_ratings:.1f}%", "1–2 star reviews", accent=True)
        st.caption("Different brands have different review counts and sampling composition. Comparisons are directional, not a controlled market benchmark.")
    with c2:
        artwork("headphone_wall.webp", "ALL BRANDS / CUSTOMER VOICE", 330)
    with st.expander("Show exact brand comparison data"):
        st.dataframe(brands.rename(columns={"brand_name":"Brand", "reviews":"Reviews", "avg_rating":"Average stars", "percentage_of_low_ratings":"Low-rated (%)"}),
                     hide_index=True, use_container_width=True)

elif page.startswith("03"):
    section("Product finding", "STUDIO PRO BUILDS TRUST. SOLO 4 CARRIES RISK.",
            "Choose a model family, explore the rating gap, then go one layer deeper into the individual Amazon listings.")
    c1, c2 = st.columns(2)
    with c1: kpi("Studio Pro", "4.51★", "199 reviews · 1.0% low-rated", accent=False)
    with c2: kpi("Solo 4", "4.34★", "300 reviews · 11.3% low-rated", accent=True)
    family_metric = st.radio("Family-level measure", ["Average rating", "Low-rated %"], horizontal=True)
    l, r = st.columns([1.6, .9], gap="large")
    with l: display_chart(model_comparison_chart(families, family_metric))
    with r:
        artwork("broken.webp", "RISK IS NOT UNIFORM", 390)
    note("The low-rating rate for Solo 4 is more than ten times Studio Pro's in this review sample. That is a signal to investigate—not proof of a product-wide defect.", alert=True)
    section("Listing-level drilldown", "THE SAME MODEL. VERY DIFFERENT SIGNALS.",
            "The five Amazon ASINs in the notebook show why aggregate model averages can hide concentrated issues.")
    l1, l2 = st.columns([2, 1], gap="large")
    with l1:
        filter_fam = st.selectbox("Product family", ["All listings", "Solo 4", "Studio Pro"])
    with l2:
        asin_metric = st.radio("Listing measure", ["Average rating", "Low-rated %"], horizontal=True)
    part = asins.copy()
    if filter_fam != "All listings":
        part = part[part.product_name.str.contains(filter_fam, regex=False, na=False)]
    display_chart(asin_chart(part, asin_metric))
    pick = st.selectbox("Inspect a listing", part.product_asin.tolist(), format_func=lambda a: f"{a} — {part.loc[part.product_asin == a, 'product_name'].iloc[0]}")
    row = part[part.product_asin == pick].iloc[0]
    cols = st.columns(3)
    with cols[0]: kpi("ASIN reviews", str(int(row.reviews)))
    with cols[1]: kpi("Average rating", f"{row.avg_rating:.2f}★")
    with cols[2]: kpi("Low-rated share", f"{row.percent_low_ratings:.1f}%", "1–2 stars")
    st.caption("ASIN-level results come from the analysis notebook. Differences might reflect listings, review mix, fulfillment, or product issues; root-cause analysis is needed.")

elif page.startswith("04"):
    section("Customer feedback", "WHAT KEEPS PEOPLE. WHAT BREAKS TRUST.",
            "Explore customer themes from the presentation. Mention categories can overlap, so percentages are not additive.")
    mode = st.radio("Explore", ["What customers value", "Trust-breakers"], horizontal=True)
    is_negative = mode == "Trust-breakers"
    frame = negative_themes if is_negative else positive_themes
    count = 36 if is_negative else 432
    c1, c2 = st.columns([1.55, .8], gap="large")
    with c1:
        kpi("Low-rated Beats reviews" if is_negative else "Positive Beats reviews", str(count),
            "1–2 stars" if is_negative else "4–5 stars", accent=is_negative)
        display_chart(themes_chart(frame, mode))
    with c2:
        artwork("broken.webp" if is_negative else "city_listener.webp",
                "PREMIUM EXPECTATIONS" if is_negative else "WHY CUSTOMERS CHOOSE BEATS", 495)
    if is_negative:
        section("Customer voices", "THE DETAILS BECOME THE DEALBREAKERS.")
        with st.expander("Representative negative review quotes", expanded=True):
            st.markdown('> “One side is no longer working.”\n\n> “Won’t charge now.”\n\n> “They hurt your ears after 10–15 mins.”')
        note("Only 36 Beats reviews were low-rated. These are directional complaint-language signals, not measured hardware defect rates. Confirm them with returns, warranty and support data.", alert=True)
    else:
        note("Sound, perceived quality, comfort, value and battery support the brand. The slide-reported theme percentages are intentionally preserved; some percentages differ from a later notebook summary.")

elif page.startswith("05"):
    section("Product strategy", "STABILIZE. POSITION. THEN CONCEPT-TEST.",
            "The presentation recommends validation before launch approval. Use the checklist to see what evidence the next phase needs.")
    l, r = st.columns([1.55, .8], gap="large")
    with l:
        phases = [
            ("01  Investigate Solo 4 risk", "Diagnose reliability, charging, comfort, listing performance, fulfillment and value perception."),
            ("02  Strengthen Studio Pro", "Position Studio Pro as the premium anchor: emphasize sound, ANC, Apple compatibility, comfort and reliability."),
            ("03  Concept-test everyday premium", "Test a comfort-first concept with commuters, students, remote workers and frequent listeners."),
            ("04  Build the business case", "Estimate revenue, contribution margin, development cost, ROI and formal launch thresholds."),
        ]
        for title, detail in phases:
            with st.expander(title, expanded=title.startswith("01")):
                st.write(detail)
        st.markdown("### Validation checklist")
        for item in ["Root cause of Solo 4 complaints", "Returns, warranty and support analysis",
                     "Segmentation beyond Amazon reviewers", "Concept testing and purchase intent",
                     "Willingness to pay", "Financial scenario model and launch thresholds"]:
            st.checkbox(item, key=f"validation_{item}")
        note("Final takeaway: fix trust first. Anchor premium with Studio Pro. Investigate Solo 4. Validate the comfort-first concept. Launch only when the evidence supports it.")
    with r:
        artwork("meeting.webp", "PRODUCT STRATEGY WORKSHOP", 360)
        st.write("")
        artwork("concept.webp", "FUTURE CUSTOMER / CONCEPT TEST", 350)
    section("Decision framing", "WHAT THE CURRENT DATA CAN — AND CANNOT — SAY.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Supported by the analysis**")
        st.markdown("- Beats has meaningful positive customer feedback.\n- Studio Pro outperforms Solo 4 in this sample.\n- Reliability, comfort and value language identify trust risks.\n- Product- and ASIN-level analysis helps target investigation.")
    with c2:
        st.markdown("**Needs validation before launch**")
        st.markdown("- Broader market demand and buyer segmentation.\n- Demand for a new comfort-first product.\n- Willingness to pay and purchase intent.\n- Return rates, defect attribution, costs and ROI.")

elif page.startswith("06"):
    section("Real review explorer", "THE REVIEWS. NOT JUST THE SLIDES.",
            "Explore 1,300 cleaned Amazon reviews behind the analysis. Every chart here "
            "recalculates from your selected brands, products, years, ratings and search terms.")
    with st.expander("Dataset details / optional CSV replacement", expanded=False):
        st.markdown("**Included source:** `amazon_headphone_reviews.csv` (or `data/`) · "
                    "1,374 original rows → 74 duplicates removed → **1,300 reviews**.")
        st.caption("Cleaning mirrors the notebook: valid 1–5 star ratings and deduplication "
                   "by reviewer name, product name, and review content. The other dashboard "
                   "sections preserve the original presentation/notebook snapshots.")
        raw_file = st.file_uploader("Replace with another reviews CSV (optional)",
                                    type=["csv"], key="raw_csv")
    if raw_file is None:
        raw = load_packaged_reviews()
        source_label = "BUILT-IN REVIEW DATA"
    else:
        try:
            raw = clean_reviews(pd.read_csv(raw_file, low_memory=False))
        except Exception as exc:
            st.error(f"Could not use this CSV: {exc}")
            st.stop()
        source_label = "UPLOADED REVIEW DATA"

    st.markdown(f'<div class="section-label">{source_label} · {len(raw):,} CLEAN REVIEWS</div>',
                unsafe_allow_html=True)
    if raw.empty:
        st.warning("No valid 1–5 star reviews were found in the data.")
        st.stop()

    # All controls operate on the actual record-level sample.
    first, second, third = st.columns([1.3, 1.2, 1], gap="medium")
    with first:
        selected_brands = st.multiselect("Brands", sorted(raw["brand_name"].unique()),
                                        default=sorted(raw["brand_name"].unique()))
    with second:
        selected_sentiments = st.multiselect(
            "Rating groups", ["Positive", "Neutral", "Low-rated"],
            default=["Positive", "Neutral", "Low-rated"])
    with third:
        verified = st.selectbox("Purchase verification", ["All reviews", "Verified", "Unverified"])

    view = raw[raw["brand_name"].isin(selected_brands) &
               raw["sentiment"].isin(selected_sentiments)].copy()
    if verified != "All reviews" and "verified_purchase" in view.columns:
        flag = pd.to_numeric(view["verified_purchase"], errors="coerce")
        view = view[flag.eq(1 if verified == "Verified" else 0)]

    left, middle, right = st.columns([1.5, 1, 1.4], gap="medium")
    with left:
        products = sorted(view["product_name"].dropna().astype(str).unique()) if "product_name" in view.columns else []
        product_selection = st.selectbox("Product / model", ["All products"] + products)
    with middle:
        if "date_of_review" in view.columns:
            years = sorted(view["date_of_review"].dt.year.dropna().astype(int).unique().tolist())
            chosen_years = st.multiselect("Review years", years, default=years)
        else:
            chosen_years = []
            st.caption("No date information in this source.")
    with right:
        search_text = st.text_input("Search reviews", placeholder="Try comfort, ANC, charging …")

    if product_selection != "All products":
        view = view[view["product_name"].astype(str).eq(product_selection)]
    if "date_of_review" in view.columns and chosen_years is not None:
        view = view[view["date_of_review"].dt.year.isin(chosen_years)]
    review_cols = [c for c in ["product_review_title", "review_content"] if c in view.columns]
    if search_text and review_cols:
        review_text = view[review_cols].fillna("").astype(str).agg(" ".join, axis=1)
        view = view[review_text.str.contains(search_text, regex=False, case=False, na=False)]
    elif search_text:
        st.warning("This data source does not contain review-text columns.")

    if view.empty:
        st.warning("No reviews match those filters. Try a different brand, date or search term.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        with m1: kpi("Matching reviews", f"{len(view):,}", "Live sample", accent=True)
        with m2: kpi("Average rating", f"{view['rating'].mean():.2f}★", "Out of five")
        with m3: kpi("Positive", f"{view['rating'].ge(4).mean()*100:.1f}%", "4–5 star reviews")
        with m4: kpi("Low-rated", f"{view['rating'].le(2).mean()*100:.1f}%", "1–2 star reviews")

        section("Dynamic comparisons", "FIND THE PATTERNS.",
                "Use these views to compare live subsets, rather than the fixed snapshot from the slides.")
        chart_left, chart_right = st.columns([1.35, 1], gap="large")
        with chart_left:
            metric = st.radio("Brand comparison", ["Average star rating", "Low rating %"],
                              horizontal=True, key="explorer_brand_metric")
            agg = view.groupby("brand_name", as_index=False).agg(
                reviews=("rating", "size"),
                avg_rating=("rating", "mean"),
                percentage_of_low_ratings=("rating", lambda s: 100 * s.le(2).mean()),
            )
            display_chart(brand_chart(agg, metric, 425))
        with chart_right:
            st.markdown("#### Star distribution")
            rating_counts = (view["rating"].astype(int).value_counts()
                             .reindex([1, 2, 3, 4, 5], fill_value=0))
            dist = go.Figure(go.Bar(
                x=[f"{n}★" for n in rating_counts.index],
                y=rating_counts.values,
                marker_color=[RED, RED, "#9d6a6e", PINK, PINK],
                text=rating_counts.values,
                textposition="outside",
                hovertemplate="Rating: %{x}<br>Reviews: %{y:,}<extra></extra>",
            ))
            chart_style(dist, 370, xgrid=False)
            dist.update_layout(xaxis_title="Review rating", yaxis_title="Review count")
            display_chart(dist)

        if "date_of_review" in view.columns and view["date_of_review"].notna().any():
            st.markdown("#### Changes over time")
            time_mode = st.radio("View", ["Review volume", "Average rating"],
                                 horizontal=True, key="explorer_time_metric")
            trend = (view.dropna(subset=["date_of_review"])
                     .assign(year=lambda f: f["date_of_review"].dt.year)
                     .groupby("year", as_index=False)
                     .agg(reviews=("rating", "size"), avg_rating=("rating", "mean")))
            trend["year"] = trend["year"].astype(str)
            if time_mode == "Review volume":
                yearly = go.Figure(go.Bar(
                    x=trend["year"], y=trend["reviews"], marker_color=RED,
                    text=trend["reviews"], textposition="outside",
                    hovertemplate="Year: %{x}<br>Reviews: %{y:,}<extra></extra>"))
                yearly.update_layout(yaxis_title="Reviews")
            else:
                yearly = go.Figure(go.Scatter(
                    x=trend["year"], y=trend["avg_rating"], mode="lines+markers+text",
                    line=dict(color=RED, width=3), marker=dict(color=PINK, size=10),
                    text=[f"{v:.2f}★" for v in trend["avg_rating"]], textposition="top center",
                    customdata=trend["reviews"],
                    hovertemplate="Year: %{x}<br>Average: %{y:.2f}★"
                                  "<br>Reviews: %{customdata:,}<extra></extra>"))
                yearly.update_layout(yaxis_title="Average rating (out of 5)")
                yearly.update_yaxes(range=[0, 5.2])
            chart_style(yearly, 310, xgrid=False)
            yearly.update_xaxes(type="category", title_text="Review year")
            if time_mode == "Average rating":
                yearly.update_yaxes(range=[0, 5.2])
            display_chart(yearly)
            st.caption("Years reflect the available review dates, not a random or representative market sample. "
                       "Rating changes should be interpreted alongside review counts.")

        st.markdown("#### Individual customer reviews")
        sort_by = st.selectbox("Sort reviews", ["Newest first", "Lowest rating", "Highest rating"])
        if sort_by == "Newest first" and "date_of_review" in view.columns:
            view = view.sort_values("date_of_review", ascending=False)
        elif sort_by == "Lowest rating":
            view = view.sort_values("rating", ascending=True)
        elif sort_by == "Highest rating":
            view = view.sort_values("rating", ascending=False)
        show_cols = [c for c in ["brand_name", "product_name", "date_of_review", "rating",
                                 "sentiment", "product_review_title", "review_content"] if c in view.columns]
        st.dataframe(view[show_cols], use_container_width=True, hide_index=True, height=430)
        st.download_button("Download filtered reviews (CSV)",
                           view.to_csv(index=False).encode("utf-8"),
                           file_name="beats_filtered_amazon_reviews.csv", mime="text/csv")
        note("This is a convenience sample of Amazon reviews, not a representative survey of all "
             "headphone buyers. Theme rates on the Customer Signals page remain the slide-reported figures.")

elif page.startswith("07"):
    section("Presentation viewer", "THE ORIGINAL DECK. THE ORIGINAL ARTWORK.",
            "All 11 PDF slides are preserved as images so you can compare the dashboard directly with the presentation design.")
    slides = [
        "Beats by Dre — Analysis & Launch Recommendation", "The Market Is Growing — SCQA",
        "Methodology & Analysis Framework", "Growth & Rising Expectations", "Competitive Position",
        "Average Star Rating by Brand", "What Keeps Customers Choosing Beats", "Premium Trust Breaks in the Details",
        "Studio Pro vs. Solo 4", "What Beats Still Needs", "Recommended Path",
    ]
    number = st.select_slider("Choose a slide", options=list(range(1, 12)), value=1,
                              format_func=lambda i: f"{i:02d} / 11", key="slide_number")
    st.markdown(f"### {slides[number-1]}")
    st.image(str(asset_file(f"slides/slide_{number:02}.webp")), use_container_width=True)
    def move_slide(delta: int) -> None:
        st.session_state["slide_number"] = min(11, max(1, st.session_state["slide_number"] + delta))

    l, r = st.columns(2)
    with l:
        st.button("← Previous slide", disabled=number <= 1, on_click=move_slide, args=(-1,))
    with r:
        st.button("Next slide →", disabled=number >= 11, on_click=move_slide, args=(1,))
    with (asset_file("original_presentation.pdf")).open("rb") as f:
        st.download_button("Download original 11-slide PDF", f,
                           file_name="Beats_by_Dre_Analysis_and_Launch_Recommendation.pdf", mime="application/pdf")

# Persistent footer / transparency notice
st.markdown(
    '<div class="footer">BY GRACIE SCHMIDT · SOURCE: AMAZON HEADPHONE REVIEWS · '
    'ANALYSIS SNAPSHOT, NOT LIVE MARKET DATA · NOT AN OFFICIAL BEATS DASHBOARD · '
    'REVIEW INSIGHTS ARE DIRECTIONAL AND REQUIRE FURTHER VALIDATION.</div>', unsafe_allow_html=True,
)
