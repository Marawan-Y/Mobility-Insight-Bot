# Mobility Insight Platform

An AI-powered Flask web application for exploring and validating emerging mobility technology trends. Built for Schaeffler's Advanced Innovations in Mobility Solutions.

## Features
- **Identification:** Select mobility use-case & sector, input your demand.
- **Scouting:** Generates 3 trend solutions via LLM.
- **Validation:** Comprehensive assessment, radar positioning, and PESTEL analysis of each trend.
- **Implementation:** Market-ready solution steps and key partner mapping.
- Full session persistence in MySQL.

## Setup
1. **Clone repo**
2. **Install dependencies:** `pip install -r requirements.txt`
3. **Configure `.env`:**
   ```text
   SECRET_KEY=...
   DB_HOST=...
   DB_PORT=3306
   DB_NAME=mobility_bot
   DB_USER=...
   DB_PASSWORD=...
   LLM_PROVIDER=openai or vertex
   OPENAI_API_KEY=...
   VERTEX_PROJECT=...
   VERTEX_LOCATION=...
   VERTEX_MODEL=...