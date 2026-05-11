"""Streamlit admin entry point."""

from __future__ import annotations

import streamlit as st

from app.components.styles import inject_brand_css

st.set_page_config(page_title="Pulse Admin", page_icon="📊", layout="wide")
inject_brand_css()

st.title("Pulse — Admin")
st.caption("Upload campaign data, manage flights, refresh the public dashboard.")

st.info(
    "**v0.5 scaffold** — parsers + refresh pipeline working end-to-end. "
    "Upload UI, Firestore persistence, Cloud Run deploy still TBD."
)

st.subheader("Try the parser")
uploaded = st.file_uploader("Measure Studio export (.csv)", type=["csv"])
if uploaded:
    from app.parsers.measure_studio import parse

    result = parse(uploaded.getvalue())
    if result.ok:
        c1, c2, c3 = st.columns(3)
        c1.metric("Posts parsed", result.row_count)
        c2.metric("Platforms", len(result.platforms()))
        c3.metric("Post groups", len(result.post_groups()))
        st.write("**Post Groups detected:**", ", ".join(sorted(result.post_groups())) or "_(none)_")
        if result.warnings:
            st.warning("\n".join(f"- {w}" for w in result.warnings))
    else:
        st.error("\n".join(f"- {e}" for e in result.errors))
