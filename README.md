# 🍳 Smart Pantry Recipe Concierge

An AI-powered culinary assistant built with the **Google Agent Development Kit (ADK)** and **Gemini**. The Smart Pantry Recipe Concierge helps users manage their digital pantry, discover personalized recipes, remember long-term dietary restrictions, generate AI food images and videos, and locate nearby grocery stores.

![Smart Pantry Agent Demo](demo.gif)

---

## 🌟 Capabilities & Features

Based on the actual codebase implementation in `app/`, the agent leverages the following tools and Google Cloud services:

* **🧠 Long-Term Memory (Vertex AI Memory Bank)**
  * Uses `VertexAiMemoryBankService` (`LoadMemoryTool` and `PreloadMemoryTool`) to remember user dietary restrictions, allergies, and personal preferences across chat sessions.
  * Strictly filters recipe recommendations to ensure suggested dishes do not contain user-specified allergens.

* **📦 Digital Pantry & Recipe Store (Google Firestore)**
  * Integrated with a Firestore `recipes` collection.
  * `search_recipes`: Filters recipes by cuisine (e.g., Italian, Mexican, Asian) or dietary tags (e.g., vegan, quick, high-protein).
  * `get_recipe`: Retrieves full recipe details including ingredients, preparation time, and step-by-step instructions.
  * `add_recipe`: Allows adding new custom recipes directly into the Firestore digital pantry.

* **🎨 Generative Food Item Photos & Videos (Vertex AI & Cloud Storage)**
  * `generate_item_image`: Uses `gemini-3.1-flash-lite-image` (global region) to create food photos.
  * `generate_item_video`: Uses `gemini-omni-flash-preview` (global region) to generate short food item videos.
  * Automatically uploads generated media to Google Cloud Storage (`smart-pantry-media-c421a42d4a54`) and registers artifacts for display in the ADK Playground.

* **📍 Nearby Store Lookup & Geocoding (Google Maps & Places APIs)**
  * `geocode_address`: Converts location names or street addresses into geographic coordinates (`latitude` / `longitude`).
  * `find_nearby_places`: Searches for nearby grocery stores, supermarkets, and bakeries within a specified radius using the Google Places API (New).

* **🌐 Online Meal Discovery (TheMealDB API)**
  * `fetch_online_meal_ideas`: Searches public online meal databases for recipe ideas, ingredient breakdowns, thumbnails, and YouTube tutorial links.

* **✨ Generative UI Cards (A2UI v0.8)**
  * Renders rich, responsive UI cards (`Card`, `Column`, `Row`, `Text`, `Image`) directly inside the dialogue interface using custom ADK model response callbacks.

* **🔒 Python Code Execution**
  * Configured with `AgentEngineSandboxCodeExecutor` for safe code execution in a secure sandbox.

---

## 🚧 Status of Planned Features

* **Voice Audio Input/Output**: *Planned, not yet implemented.*
* **Barcode Scanner & Macro Nutrition Calculator**: *Planned, not yet implemented.*

---

## 🛠️ Architecture & Project Structure

```
.
├── app/                      # Main ADK Agent source directory
│   ├── agent.py              # Root agent, tools, Memory Bank, Firestore & Vertex AI setup
│   ├── a2ui_utils.py         # A2UI v0.8 schema manager & model response callback
│   └── fast_api_app.py       # FastAPI web server entrypoint
├── frontend/                 # Chat frontend proxy & UI layout
│   ├── main.py               # FastAPI proxy endpoint
│   └── static/               # HTML/CSS dialogue UI & A2UI renderer
├── agents-cli-manifest.yaml  # Agents CLI configuration & deployment manifest
├── demo.gif                  # Looping demo video recording
└── requirements.txt          # Python dependencies
```

---

## 🚀 Local Setup & Run Instructions

### Prerequisites

* Python 3.11+
* Google Cloud Project with Vertex AI, Firestore, and Cloud Storage enabled
* Google Maps API Key (`GOOGLE_MAPS_API_KEY`)

### Installation

1. **Clone the repository and install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set required environment variables**:
   ```bash
   export GOOGLE_MAPS_API_KEY="YOUR_KEY"
   ```

3. **Launch the local ADK Agent Playground**:
   ```bash
   uv run adk web . --port 8080 --reload_agents
   ```

4. **Or run the custom Chat Frontend proxy**:
   ```bash
   cd frontend
   export AGENT_DIRECTORY="app"
   python main.py
   ```
