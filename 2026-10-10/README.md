# 2026-10-10 — Dual-site PPG concordance gate

Fork base: https://github.com/sanhariharan/Medical-Rag-for-care-planning

One feature added: Generator–Verifier–Updater loop that refuses a glucose-risk
label unless wrist and in-ear PPG features agree, then applies the post-load
index cutoff. Educational only; not a medical device.

Run: `python gvu_dual_site_ppg.py`
