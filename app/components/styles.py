"""Pulse design tokens for the Streamlit admin app."""

from __future__ import annotations

import streamlit as st

COLORS = {
    "liquorice": "#1F1A15",
    "cream": "#F5F1E8",
    "paper": "#FAF7EF",
    "flame": "#DE6B38",
    "orange": "#FF9947",
    "pear": "#8FC766",
    "sky": "#5CB5F2",
    "lilac": "#A896F2",
    "blossom": "#F2A6A8",
    "ink": "#1F1A15",
    "ink_2": "#443c33",
    "ink_3": "#857d70",
    "positive": "#2f7a3f",
    "warning": "#FF9947",
    "danger": "#b8392b",
}


def inject_brand_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,200;0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,300;1,6..72,400&display=swap");

        .stApp {{ background: {COLORS["cream"]}; }}
        body, .stApp {{ font-family: 'Inter', sans-serif; color: {COLORS["ink"]}; }}

        h1 {{ font-family: 'Newsreader', Georgia, serif; font-weight: 300; font-size: 48px;
              letter-spacing: -0.02em; color: {COLORS["ink"]}; }}
        h2, h3 {{ font-family: 'Newsreader', Georgia, serif; font-weight: 300; }}

        [data-testid="stMetric"] {{
          background: {COLORS["paper"]}; border: 1px solid rgba(31,26,21,0.10);
          border-radius: 14px; padding: 18px 20px 16px;
        }}
        [data-testid="stMetricLabel"] {{
          font-size: 10px; font-weight: 600; letter-spacing: 0.1em;
          text-transform: uppercase; color: {COLORS["ink_3"]};
        }}
        [data-testid="stMetricValue"] {{
          font-family: 'Newsreader', Georgia, serif; font-size: 36px;
          font-weight: 300; letter-spacing: -0.02em;
        }}

        .stButton > button {{
          border-radius: 999px; border: 1px solid {COLORS["liquorice"]};
          background: {COLORS["liquorice"]}; color: {COLORS["cream"]};
          font-weight: 500; padding: 9px 18px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
