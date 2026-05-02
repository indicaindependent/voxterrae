<div align="center">

[![VoxTerrae](https://img.shields.io/badge/VoxTerrae-Geospatial_Voice_Intel-3b82f6?style=for-the-badge&logo=googlemaps&logoColor=white)](https://voxterrae.app)
[![Powered by Claude](https://img.shields.io/badge/Powered_by-Anthropic_Claude-CC785C?style=for-the-badge&logo=anthropic&logoColor=white)](https://anthropic.com)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://workers.cloudflare.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

# 🌍 VoxTerrae

### *Community-sourced ground truth from the places that matter most*

**Live:** [voxterrae.app](https://voxterrae.app)

</div>

---

## What Is VoxTerrae?

VoxTerrae ("Voice of the Earth") is a multilingual geospatial intelligence platform that aggregates and synthesizes community-sourced reports from conflict zones, disaster areas, and underreported regions — then uses **Anthropic Claude** to translate, verify, and surface the signal from the noise.

Where satellite imagery shows craters, VoxTerrae captures what residents say happened before, during, and after. Where official reports are delayed or sanitized, community voices fill the gap.

> *"Satellites see the aftermath. VoxTerrae captures what the people on the ground experienced."*

---

## The Problem

Open-source intelligence (OSINT) has a language problem:

- Most conflict reporting happens in Arabic, Farsi, Urdu, Ukrainian, Amharic — not English
- Translation tools exist but strip context and nuance
- Community reports from affected populations are drowned out by official narratives
- Real-time ground truth is siloed across Telegram channels, local forums, and social media

**The people most affected by conflict are least represented in the intelligence that shapes responses to it.**

---

## The Solution

VoxTerrae provides a structured layer for community ground-truth intelligence:

- 🗣️ **Multilingual ingestion** — reports submitted in any language, Claude handles translation + context preservation
- 📍 **Geospatial tagging** — every report pinned to a coordinate, visualized on live heatmap
- 🔍 **AI synthesis** — Claude claude-opus-4-7 identifies patterns, flags contradictions, surfaces high-confidence signals
- ✅ **Community verification** — endorsement system lets local contributors validate reports
- 🔥 **Hot zone detection** — automatic clustering of high-activity report areas
- 📡 **Real-time feed** — live updates as reports come in, filterable by region and confidence

---

## Architecture

```
Community Report (any language, any region)
       │
       ▼
Cloudflare Worker (voxterrae.app)
       │
       ├─► Language detection
       ├─► Geolocation tagging
       └─► Report storage (D1)
                   │
                   ▼
       Anthropic Claude claude-opus-4-7
       ├─► Translation (context-preserving)
       ├─► Credibility assessment
       ├─► Pattern synthesis across reports
       └─► Hot zone flagging
                   │
                   ▼
         Live heatmap + structured feed
         API endpoints for researchers
```

**Stack:**
- **Runtime:** Cloudflare Workers (edge, globally distributed)
- **AI:** Anthropic Claude claude-opus-4-7 — translation, synthesis, verification
- **Storage:** Cloudflare D1 (reports, endorsements, flags)
- **Visualization:** Leaflet.js + MarkerCluster (live geospatial heatmap)
- **No framework. No server. Sovereign edge stack.**

---

## Use Cases

| User | Use Case |
|------|----------|
| OSINT researchers | Multilingual ground truth aggregation |
| Journalists | Real-time community reporting from conflict zones |
| NGOs & humanitarian orgs | Needs assessment from affected populations |
| Academic researchers | Conflict documentation and pattern analysis |
| Community advocates | Amplify local voices to international audiences |

---

## What Makes This Different

| Feature | VoxTerrae | Traditional OSINT |
|---------|-----------|-------------------|
| Language support | Any language via Claude | English-dominant |
| Source | Community ground truth | Official/media reports |
| Latency | Real-time edge | Hours/days |
| Cost | Free to use | Expensive platforms |
| Community verification | Built-in endorsement system | Manual analyst review |

---

## Mission Alignment

VoxTerrae is a project of **[VPDLNY](https://osintnet.uk)** — Vulnerable Persons Defense League of New York.

The people most affected by conflict, disaster, and institutional failure are the least represented in the intelligence systems that shape responses to those crises. VoxTerrae is built to close that gap — putting community voices on the same map as satellite imagery and official reporting.

---

## Deployment

```bash
# Clone and configure
git clone https://github.com/indicaindependent/voxterrae
cd voxterrae
cp wrangler.toml.example wrangler.toml
# Fill in your CF account ID + Anthropic API key

# Deploy
npm install -g wrangler
wrangler deploy
```

---

## Roadmap

- [ ] Mobile submission form (SMS-based reporting for low-connectivity zones)
- [ ] Telegram channel ingestion (auto-pull from monitored channels)
- [ ] Confidence scoring model (multi-signal report verification)
- [ ] Export API for researchers (bulk download, GeoJSON format)
- [ ] Moderator dashboard with flag resolution workflow
- [ ] Integration with existing OSINT platforms (Bellingcat, ACLED)

---

## Support

VoxTerrae is free and open. If it's useful to your work:

**Bitcoin:** `bc1qyrtasy0naxauhf3yeg05ztu2x5vmx9jxjzsq2a`

---

<div align="center">
<sub>Built on Cloudflare's global edge · Powered by Anthropic Claude · Built by <a href="https://osintnet.uk">VPDLNY</a></sub><br/>
<sub>Copyright (c) 2026 Peter McVries / Indica Independent Media / VPDLNY — MIT License</sub>
</div>
