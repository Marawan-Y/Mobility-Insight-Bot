# Mobility-Insight-Bot

## Project Overview
Mobility-Insight-Bot is a Flask-based web application that provides an AI-powered assistant for exploring emerging mobility technology trends. Users can input their specific query in a structured format and receive:
1. **Trend Solutions:** Five cutting-edge technology trend solutions addressing the query, each with detailed descriptions and opportunities.
2. **Comprehensive Trend Assessment:** (Optional) A numerical evaluation of each trend across multiple criteria, summarized as an average score.
3. **Radar Positioning:** (Optional) A classification of each trend into **ACT**, **PREPARE**, or **WATCH** categories.
4. **PESTEL Trend Driver:** (Optional) Identification of the primary PESTEL (Political, Economic, Social, Technological, Ecological, Legal) driver for each trend.

The assistant interacts step-by-step, asking the user whether they want to see each subsequent level of detail. All user queries and results are stored in a MySQL database, and past conversations can be viewed from the sidebar.

## Project Structure
```
Mobility-Insight-Bot/
├── app.py               # Python backend (Flask app, routes, LLM and DB logic)
├── requirements.txt     # Python dependencies
├── README.md            # Project documentation and usage instructions
├── .env.example         # Sample environment configuration
├── schema.sql           # MySQL database schema for required table
├── templates/           # Jinja2 templates for the web interface
│   ├── base.html        # Base HTML layout (includes sidebar and common structure)
│   └── index.html       # Main chatbot interface template
└── static/              # Static files (CSS/JS)
    ├── css/style.css    # Custom styles for the UI
    └── js/chat.js       # Frontend script for auto-scrolling chat
```

## Setup and Installation
1. **Clone the repository** (or copy the project files) to your local machine.
2. **Install Python dependencies:** Ensure you have Python 3.9+ installed. It is recommended to use a virtual environment. Then run:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure the environment:** Copy `.env.example` to `.env` and fill in the required values:
   - MySQL database connection settings (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).
   - Google Cloud Vertex AI settings:
     - `PROJECT_ID`: Your Google Cloud project ID.
     - `LOCATION`: The region of your Vertex AI resources (e.g., "us-central1").
     - `SERVICE_ACCOUNT_FILE`: Path to the JSON key file for a Google Cloud service account with Vertex AI access.
     - `MODEL_NAME`: The Vertex AI model name to use (e.g., `"gemini-1.5-flash"` for the Gemini LLM).
   - `FLASK_SECRET_KEY`: A secret key for Flask session management (any random string).
4. **Set up the database:** Create a MySQL database and run the SQL commands in `schema.sql` to create the required table. Update the `.env` with the database credentials.
5. **Place the service account key file:** Ensure the Google Cloud service account JSON key file is available at the path you specified in `.env`. The service account should have permission to use Vertex AI (e.g., Vertex AI User role).

## Usage
1. **Run the Flask application:** 
   ```bash
   python app.py
   ```
   This will start the development server (by default on `http://127.0.0.1:5000/`).
2. **Open the app in a browser:** Navigate to `http://localhost:5000` (or the appropriate host/port). You will see the chatbot interface.
3. **Interact with the bot:** 
   - The bot will greet you with a welcome message and instructions on how to format your query. 
   - Input your query in the format: **Use-case, Sector, Demand** (for example: `Route Optimization, Logistics, Reduce delivery times`).
   - The assistant will respond with five trend solutions addressing your query.
   - It will then ask if you want a **Comprehensive Trend Assessment**. If you type "Yes", it will display an average numeric score for each trend (on a 1-10 scale). If "No", it will skip to the next question.
   - Next, it will ask if you want **Radar Positioning**. Respond "Yes" to see each trend labeled as ACT, PREPARE, or WATCH (indicating its priority/urgency), or "No" to skip.
   - Finally, it will ask if you want the **PESTEL Trend Driver** for each trend. "Yes" will show the primary PESTEL category driving each trend (e.g., Technological, Economic, etc.).
4. **View conversation history:** All past queries are listed in the sidebar (left side). Clicking on a past query will load the conversation details (query and results) in view-only mode. You can use this to review previous insights.
5. **Start a new query:** Click the "**New Query**" button at the top of the sidebar to reset the chat and ask a new question.

## Environment & API Keys
This application uses Google Vertex AI to access the Gemini large language model. Make sure your Google Cloud project is enabled for Vertex AI and that you have obtained a service account JSON key with the necessary permissions. The `.env` file should point to this key file and specify the project and region. No other API keys are required, as authentication is handled via the service account credentials.

## Database Schema
The application uses a single table **`trend_queries`** to log each user query and the results. The schema (also provided in `schema.sql`) is:
```sql
CREATE TABLE trend_queries (
  id INT AUTO_INCREMENT PRIMARY KEY,
  use_case VARCHAR(255),
  sector VARCHAR(255),
  demand VARCHAR(255),
  trend_solutions MEDIUMTEXT,
  trend_assessment TEXT,
  radar_positioning TEXT,
  pestel_tag TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
Each row corresponds to one conversation (user query). The columns store the user input and each level of result:
- **trend_solutions:** The detailed output of five trend solutions (textual).
- **trend_assessment:** The average score (numeric evaluation) per solution (as text, comma-separated).
- **radar_positioning:** The radar category (ACT/PREPARE/WATCH) for each solution (comma-separated).
- **pestel_tag:** The primary PESTEL driver for each solution (comma-separated).

## Running the App
After installation and configuration, start the app (as described above) and interact through the web UI. The Flask server will handle requests to the Vertex AI API to obtain responses from the Gemini LLM. Ensure that your machine has internet access and the Google Cloud credentials are correctly set up for the API calls to succeed.

---
**Note:** The first request to the Vertex AI model may take a bit longer due to model initialization. Subsequent responses should be faster. All data is stored in the MySQL database; no conversation data is stored in the application server beyond the session state for the current conversation.
