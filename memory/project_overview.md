# FOS Campaign Performance Tracker — Project Overview

## Problem

Front Office Sports executes **50+ sponsored campaigns per year** across paid social, longform content (full episodes), and social cutdowns. Reporting is currently extremely manual:

- Export from multiple platforms (Measure Studio when working, otherwise Meta/TikTok/X Ads Managers, plus in-platform exports for LinkedIn/IG/FB/TikTok organic)
- Combine sources together with formulas in Google Sheets
- Hand-edit static HTML dashboards (`sponsored-content.html`, `sponsored-content-social.html`)
- Push to GitHub, deploy to Netlify, share new URL

Two existing dashboards are the design spec for what the team wants to see:
- `~/Documents/fos-dashboards/partner-campaigns/sponsored-content/sponsored-content.html` (longform with cutdowns: ADP, State Farm, E*TRADE)
- `~/Documents/fos-dashboards/partner-campaigns/sponsored-content/sponsored-content-social.html` (sponsored social: TastyTrade, Comcast Business)

This breaks at scale. Need a real internal tool.

## Goal

A single internal application that:
1. **Live tracking** during flight — pacing, optimization callouts, mid-flight intervention
2. **Final recap** at completion — same data, presentation-ready (recaps then exported via Claude Design)
3. **Portfolio view** — all active campaigns at a glance for cross-functional team
4. **Per-campaign deep dive** — full metric breakdown, top performers, platform splits
5. Self-serve uploads — content strategy team uploads CSVs without touching code/git

## Two campaign archetypes

Both have to work in the same system, with different default views:

1. **Sponsored social** — boosted posts across Meta/TikTok/X/LinkedIn/IG; flat structure, post-level metrics roll up to campaign
2. **Longform with cutdowns** — full episodes (typically YouTube) + social cutdowns; adds format dimension (full episode vs cutdown), length, multiple boosting methods per asset; episodes often have their own sub-pacing

## Lifecycle

Campaigns move through: **Planned → Live → Complete → Archived**. Each state changes what's shown:
- **Live** = pacing bars, status pills, optimization alerts, refreshed twice/week (daily for tight-window flights like US Bank x NFL Draft)
- **Complete** = locked snapshot, recap-ready
- **Archived** = historical reference, feeds future benchmarks

## Build philosophy

User prefers **build from scratch** over Retool/internal-tool platforms. Measure Studio was meant to be this solution but lacks customizability for FOS-specific dashboards and tracking.
