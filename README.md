# BTC Power Curve Fear & Greed

Vercel-ready Bitcoin fear-and-greed site.

The site does two things:

- serves a static frontend from `index.html`, `styles.css`, and `main.js`
- serves live market/model data from the Python serverless endpoint at `/api/snapshot`

## Model

- `fair value` means the power-curve value for the current date
- `fear & greed score` is the percentile of Bitcoin's historical deviation from that curve
- `one year out` means following the same power curve forward by 365 days

## Deploy On Vercel

1. Import this repo into Vercel.
2. Framework preset: `Other`.
3. Root directory: repo root.
4. Deploy.

Vercel will:

- serve the static frontend files directly
- run `api/snapshot.py` as a Python serverless function

## Local Notes

- The frontend is plain HTML/CSS/JS.
- The API logic lives in [powercurve_core.py](/Users/gabe/projects/btc-power/powercurve_core.py).
- Historical data is bundled in [btc_historical.csv](/Users/gabe/projects/btc-power/btc_historical.csv).
