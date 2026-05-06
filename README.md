<div align="center">

# 🌍 VoxTerrae
### *Community-Sourced Ground Truth from Conflict Zones & Crisis Regions*

<br/>

[![🔵 Live App](https://img.shields.io/badge/🔵_LIVE-voxterrae.app-3b82f6?style=for-the-badge&logo=cloudflare&logoColor=white)](https://voxterrae.app)
[![Anthropic Partner](https://img.shields.io/badge/Anthropic-Claude_Powered-CC785C?style=for-the-badge&logo=anthropic&logoColor=white)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge&logo=opensourceinitiative&logoColor=white)](LICENSE)

<br/>

![Claude](https://img.shields.io/badge/Claude-3.5_Sonnet-CC785C?style=flat-square&logo=anthropic&logoColor=white)
![Cloudflare Workers](https://img.shields.io/badge/Cloudflare_Workers-F38020?style=flat-square&logo=cloudflare&logoColor=white)
![Multilingual](https://img.shields.io/badge/Languages-50+-6366f1?style=flat-square&logo=googletranslate&logoColor=white)
![Geospatial](https://img.shields.io/badge/Geospatial-Leaflet.js-199900?style=flat-square&logo=leaflet&logoColor=white)
![Real-Time](https://img.shields.io/badge/Real--Time-WebSocket-0ea5e9?style=flat-square)

<br/>

![Status](https://img.shields.io/badge/Status-🔵_Beta-3b82f6?style=flat-square)
![Reports](https://img.shields.io/badge/Community_Reports-Live-ef4444?style=flat-square)
![Coverage](https://img.shields.io/badge/Coverage-Global-6d28d9?style=flat-square)
![Free](https://img.shields.io/badge/Free-Forever-22c55e?style=flat-square)

</div>

---

## 🌐 What Is VoxTerrae?

**VoxTerrae** ("Voice of the Earth") is a multilingual geospatial intelligence platform that aggregates community-sourced reports from **conflict zones, disaster areas, and underreported regions** — then uses **Anthropic Claude** to translate, verify, and surface the signal from the noise.

When mainstream media goes dark, the people on the ground don't.

---

## ⚡ Features

| Feature | Description |
|---|---|
| 🌍 **Geospatial Mapping** | Pin-precise reports on a live world map |
| 🗣️ **Multilingual AI** | Claude translates & synthesizes 50+ languages in real-time |
| ✅ **Verification Layer** | Community endorsement + AI cross-reference scoring |
| 🔥 **Hot Zone Detection** | Automatic clustering of high-activity regions |
| 📡 **Live Feed** | Streaming report updates without page reload |
| 🏳️ **Anonymous Posting** | No accounts required for report submission |
| 🔎 **AI Synthesis** | Ask questions about any region, get sourced answers |

---

## 🛠️ Tech Stack

```
AI Engine:    Anthropic Claude 3.5 Sonnet
Backend:      Cloudflare Workers (Edge Runtime)
Database:     Cloudflare D1 (SQLite) + KV (cache)
Frontend:     Leaflet.js · Vanilla JS · WebSocket
Translation:  Claude multilingual inference
Hosting:      Cloudflare Global Network (330+ PoPs)
```

---

## 🗂️ Architecture

```
Community Report → VoxTerrae Edge Worker
                 → Claude Translation + Verification
                 → D1 Database (geospatial index)
                 → Live Map + Feed
                 → AI Synthesis Engine
```

---

## 🏃 Quick Start

```bash
git clone https://github.com/indicaindependent/voxterrae
cd voxterrae
wrangler deploy
```

---

<div align="center">

**Built by [Indica Independent Media](https://osintnet.uk) · [VPDLNY](https://osintnet.uk) · Staten Island, NYC**

*When the media goes silent, the ground speaks.*

[![Follow on Bluesky](https://img.shields.io/badge/Bluesky-@indicaindependent-0085ff?style=flat-square&logo=bluesky&logoColor=white)](https://bsky.app/profile/indicaindependent.bsky.social)

</div>