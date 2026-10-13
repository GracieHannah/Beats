# Beats by Dre — Interactive Product Intelligence Dashboard

A Streamlit portfolio dashboard based on the **Beats by Dre Headphones Analysis & Launch Recommendation** presentation and the associated Jupyter notebook by Gracie Schmidt.

## Run it locally

1. Unzip this folder and open a terminal in the `beats_interactive_dashboard` directory.
2. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
3. Launch:
   ```bash
   streamlit run app.py
   ```
4. Streamlit will print a local URL, usually `http://localhost:8501`.

To deploy on **Streamlit Community Cloud**, upload the directory contents to a GitHub repository and select `app.py` as the entry point.

## Interactivity

- **Overview** — presentation-inspired hero, headline KPIs, competitor ratings, 4-phase roadmap.
- **Competitive position** — select brands and toggle average rating vs. 1–2 star share.
- **Product diagnostics** — compare Studio Pro and Solo 4; inspect ASIN-level ratings and low-rating rates.
- **Customer signals** — toggle positive and negative review themes, see the original presentation's caveats and illustrative quotes.
- **Launch strategy** — explore recommendations and use a session-only validation checklist.
- **Review explorer** — preloaded with **all 1,300 cleaned Amazon reviews**. Filter by brand, product, rating group, verified purchase, year and keywords. Dynamically compare brands, inspect ratings and trends, read actual review text, or download any filtered subset. You may optionally replace the included source with another CSV.
- **Original slides** — view and download the original 11-slide PDF in its exact original design.

## Data and design provenance

- `data/brand_summary.csv`, `data/family_summary.csv`, `data/asin_summary.csv` were extracted from the **saved output tables** in the uploaded notebook, not guessed or generated from synthetic reviews.
- `data/*_themes_presentation.csv` preserves the approximate percentages **displayed in the PDF slides**, even where they differ from later computations shown in the notebook. They are *slide-reported percentages*, not independently recomputed.
- `assets/*.webp` contains the user's original presentation artwork, extracted from the PDF. `assets/slides/` holds rendered previews of each slide, and `assets/original_presentation.pdf` is the source PDF.
- `data/amazon_headphone_reviews.csv` is the **user-provided, original 1,374-row dataset** (not synthetic). The app removes 74 duplicate reviews using the notebook's deduplication keys, yielding 1,300 cleaned reviews. The initial five content tabs intentionally retain the presentation/notebook snapshots; the Review Explorer computes its views from raw records at runtime.
- The review sample is directional, not proof of consumer demand or product defect rates. Negative-review themes can overlap; their percentages should not be summed.

## Included data and optional replacement CSV

Minimum columns: `brand_name`, `rating`. Recommended: `product_name`, `product_asin`, `product_review_title`, `review_content`, `date_of_review`, `user_name`.

The included CSV is loaded automatically when the Review Explorer opens. To use a different file, expand **Dataset details / optional CSV replacement** on that page. The explorer applies the notebook's basic cleaning pattern: drops rows without valid ratings/brands; keeps ratings between 1 and 5; removes duplicates based on `user_name`, `product_name` and `review_content` when all are present; and classifies 4–5★ as positive, 3★ neutral, and 1–2★ low-rated.

## A note on fidelity

This is a **functional web dashboard** inspired by the presentation and directly reusing its illustrations, fonts/style cues, and findings. PDF slide layouts are not editable application components; the original-slide viewer preserves their exact appearance separately from the interactive charts.
