---
title: Bitcoin Power Curve
emoji: ⚡
colorFrom: yellow
colorTo: yellow
sdk: gradio
sdk_version: "5.50.0"
app_file: app.py
pinned: false
---

# BTC Power Curve Temperature

A Gradio site that explains where Bitcoin sits relative to its long-run power curve and translates that into a simple market temperature:

- `Freezing` and `Cold` when BTC is trading in historically washed-out territory.
- `Balanced` when BTC is near the middle of its historical power-curve range.
- `Warm` and `Overheated` when BTC is materially above trend and greed is rising.

The dashboard combines:

- live BTC/USD spot pricing when available
- a long-run power curve model
- a percentile-based Heat Score from Bitcoin's full historical deviation versus the curve
- plain-English copy so visitors can immediately understand whether the market looks hot or cold

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```
