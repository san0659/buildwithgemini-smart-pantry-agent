# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import json
import os
import urllib.parse
import urllib.request
import uuid

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.load_memory_tool import LoadMemoryTool
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types
from google.genai import types as genai_types

from .a2ui_utils import a2ui_callback

# CRITICAL: Hardcode the GCP Project ID string. Do NOT use GOOGLE_CLOUD_PROJECT
# or google.auth.default() as those return the project NUMBER when deployed.
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-c421a42d4a54"
BUCKET_NAME = "smart-pantry-media-c421a42d4a54"
MEMORY_ENGINE_ID = "9213654553088491520"
DEPLOYMENT_METADATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "deployment_metadata.json")

# Configure Memory Bank service for future redeployments
memory_service = VertexAiMemoryBankService(
    project=FIRESTORE_PROJECT_ID,
    location="us-east1",
    agent_engine_id=MEMORY_ENGINE_ID,
)


def get_code_executor():
    """Initializes AgentEngineSandboxCodeExecutor using remote reasoning engine ID from deployment_metadata.json if present."""
    if os.path.exists(DEPLOYMENT_METADATA_PATH):
        try:
            with open(DEPLOYMENT_METADATA_PATH, "r") as f:
                metadata = json.load(f)
                remote_agent_runtime_id = metadata.get("remote_agent_runtime_id")
                if remote_agent_runtime_id:
                    return AgentEngineSandboxCodeExecutor(agent_engine_resource_name=remote_agent_runtime_id)
        except Exception:
            pass
    return AgentEngineSandboxCodeExecutor()


def get_firestore_client():
    return firestore.Client(project=FIRESTORE_PROJECT_ID)


def search_recipes(cuisine: str = "", dietary_tag: str = "") -> str:
    """Searches for recipes in the Firestore database by cuisine or dietary tag.

    Args:
        cuisine: Optional cuisine filter string (e.g. 'Italian', 'Asian', 'American').
        dietary_tag: Optional dietary tag filter string (e.g. 'vegan', 'quick', 'high-protein').

    Returns:
        A list of matching recipe summaries.
    """
    db = get_firestore_client()
    recipes_ref = db.collection("recipes")
    docs = recipes_ref.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        match_cuisine = not cuisine or cuisine.lower() in data.get("cuisine", "").lower()
        tags = [t.lower() for t in data.get("dietary_tags", [])]
        match_tag = not dietary_tag or dietary_tag.lower() in tags

        if match_cuisine and match_tag:
            results.append({
                "recipe_id": data.get("recipe_id"),
                "title": data.get("title"),
                "cuisine": data.get("cuisine"),
                "prep_time_minutes": data.get("prep_time_minutes"),
                "dietary_tags": data.get("dietary_tags")
            })

    if not results:
        return f"No recipes found matching cuisine='{cuisine}' and tag='{dietary_tag}'."
    return str(results)


def get_recipe(recipe_id: str) -> str:
    """Retrieves full recipe details including ingredients and instructions from Firestore.

    Args:
        recipe_id: The unique ID string of the recipe (e.g., 'spaghetti-carbonara').

    Returns:
        A string containing full details of the requested recipe.
    """
    db = get_firestore_client()
    doc_ref = db.collection("recipes").document(recipe_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Recipe with ID '{recipe_id}' was not found in the database."
    return str(doc.to_dict())


def add_recipe(title: str, cuisine: str, prep_time_minutes: int, ingredients: list[str], instructions: list[str], dietary_tags: list[str] = None) -> str:
    """Adds a new recipe document to the Firestore database.

    Args:
        title: Title of the recipe.
        cuisine: Cuisine category (e.g. Italian, Mexican, Asian).
        prep_time_minutes: Preparation time in minutes.
        ingredients: List of ingredient strings.
        instructions: List of step-by-step instruction strings.
        dietary_tags: Optional list of dietary tags (e.g. ['vegan', 'quick']).

    Returns:
        Confirmation message with the created recipe ID.
    """
    db = get_firestore_client()
    recipe_id = title.lower().replace(" ", "-").replace("&", "and")
    doc_data = {
        "recipe_id": recipe_id,
        "title": title,
        "cuisine": cuisine,
        "prep_time_minutes": prep_time_minutes,
        "servings": 2,
        "ingredients": ingredients,
        "instructions": instructions,
        "dietary_tags": dietary_tags or []
    }
    db.collection("recipes").document(recipe_id).set(doc_data)
    return f"Recipe '{title}' successfully saved to Firestore with ID '{recipe_id}'."


def generate_recipe_image(recipe_title: str, visual_prompt: str = "") -> str:
    """Generates a visual dish preview image for a recipe and uploads it to Cloud Storage.

    Args:
        recipe_title: Title of the dish (e.g. 'Classic Spaghetti Carbonara').
        visual_prompt: Optional extra visual description.

    Returns:
        The public HTTP URL of the generated recipe image.
    """
    filename = f"recipe_{recipe_title.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}.svg"
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#1e293b" />
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f59e0b" />
      <stop offset="100%" stop-color="#ef4444" />
    </linearGradient>
  </defs>
  <rect width="600" height="400" rx="16" fill="url(#bg)"/>
  <circle cx="300" cy="170" r="90" fill="#334155" stroke="url(#accent)" stroke-width="6"/>
  <text x="300" y="185" font-family="sans-serif" font-size="64" text-anchor="middle" fill="#f59e0b">🍳</text>
  <text x="300" y="310" font-family="sans-serif" font-size="24" font-weight="bold" text-anchor="middle" fill="#ffffff">{recipe_title}</text>
  <text x="300" y="345" font-family="sans-serif" font-size="14" text-anchor="middle" fill="#94a3b8">Smart Pantry Recipe Concierge</text>
</svg>"""

    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(svg_content, content_type="image/svg+xml")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return f"Generated visual recipe image for '{recipe_title}' available at: {public_url}"


def generate_item_image(item_name: str, tool_context: ToolContext) -> str:
    """Generates an image for a food item using gemini-3.1-flash-lite-image model in global region.

    Saves the generated image as a Playground artifact and uploads the image bytes to Cloud Storage.

    Args:
        item_name: Name of the food item or dish to generate an image for (e.g. 'Avocado Toast').

    Returns:
        The public HTTPS URL of the uploaded image on Google Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    prompt = f"Generate a photo of a delicious food item: {item_name}"

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
    )

    part = response.candidates[0].content.parts[0]
    image_bytes = part.inline_data.data
    mime_type = part.inline_data.mime_type or "image/jpeg"

    filename = f"item_{item_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}.jpg"

    # 1. Save artifact for Playground Artifacts panel
    artifact_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same image bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket("smart-pantry-media-c421a42d4a54")
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/smart-pantry-media-c421a42d4a54/{filename}"
    return public_url


def generate_item_video(item_name: str, tool_context: ToolContext) -> str:
    """Generates a short video for a food item using Google's Omni model (gemini-omni-flash-preview) in global region.

    Saves the generated video as a Playground artifact and uploads the video bytes to Cloud Storage.

    Args:
        item_name: Name of the food item or dish to generate a video for (e.g. 'Cooking Spaghetti Carbonara').

    Returns:
        The public HTTPS URL of the uploaded video on Google Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    prompt = f"Generate a short video of a delicious food item or recipe: {item_name}"

    try:
        response = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
            response_modalities=["video"],
        )
        if getattr(response, "output_video", None) and getattr(response.output_video, "data", None):
            raw = response.output_video.data
            video_bytes = base64.b64decode(raw) if isinstance(raw, str) else bytes(raw)
            mime_type = getattr(response.output_video, "mime_type", "video/mp4") or "video/mp4"
        else:
            raise ValueError("No direct output_video data returned from interactions.create")
    except Exception:
        response = client.models.generate_content(
            model="gemini-omni-flash-preview",
            contents=prompt,
        )
        part = response.candidates[0].content.parts[0]
        video_bytes = part.inline_data.data
        mime_type = part.inline_data.mime_type or "video/mp4"

    filename = f"item_video_{item_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}.mp4"

    # 1. Save artifact for Playground Artifacts panel
    artifact_part = genai_types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same video bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket("smart-pantry-media-c421a42d4a54")
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/smart-pantry-media-c421a42d4a54/{filename}"
    return public_url


def fetch_online_meal_ideas(query: str) -> str:
    """Searches the public TheMealDB API for online meal ideas, instructions, and video links.

    Args:
        query: Search query for a dish or main ingredient (e.g. 'pasta', 'chicken', 'tacos').

    Returns:
        A list of matching recipe ideas with instructions and online meal metadata.
    """
    api_key = os.environ.get("THEMEALDB_API_KEY", "1")
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php?s={encoded_query}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartPantryAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            meals = data.get("meals")
            if not meals:
                return f"No online meals found matching query '{query}'."

            results = []
            for meal in meals[:3]:
                ingredients = []
                for i in range(1, 21):
                    ing = meal.get(f"strIngredient{i}")
                    meas = meal.get(f"strMeasure{i}")
                    if ing and ing.strip():
                        ingredients.append(f"{meas.strip() if meas else ''} {ing.strip()}".strip())

                results.append({
                    "meal_id": meal.get("idMeal"),
                    "title": meal.get("strMeal"),
                    "category": meal.get("strCategory"),
                    "area": meal.get("strArea"),
                    "ingredients": ingredients[:8],
                    "thumbnail": meal.get("strMealThumb"),
                    "youtube_tutorial": meal.get("strYoutube")
                })
            return str(results)
    except Exception as e:
        return f"Error fetching online meal ideas: {e}"


def geocode_address(address: str) -> str:
    """Converts a street address or location name into geographic coordinates (latitude and longitude).

    Args:
        address: The address or location string to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary string containing formatted address, latitude, and longitude.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if not results:
                return f"No location found for address '{address}'."

            first_result = results[0]
            location = first_result.get("geometry", {}).get("location", {})
            return str({
                "formatted_address": first_result.get("formatted_address"),
                "latitude": location.get("lat"),
                "longitude": location.get("lng")
            })
    except Exception as e:
        return f"Geocoding error: {e}"


def find_nearby_places(latitude: float, longitude: float, place_type: str = "grocery_store", radius_meters: int = 5000) -> str:
    """Finds nearby places (e.g., grocery stores, supermarkets) around given coordinates using Places API (New).

    Args:
        latitude: Latitude of the center location.
        longitude: Longitude of the center location.
        place_type: Type of place to search for (e.g. 'grocery_store', 'supermarket', 'bakery').
        radius_meters: Radius in meters for the search circle (default: 5000).

    Returns:
        A list of nearby places with name, formatted address, and coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
    }
    body = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(latitude),
                    "longitude": float(longitude)
                },
                "radius": float(radius_meters)
            }
        }
    }

    try:
        json_data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=json_data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            places = data.get("places", [])
            if not places:
                return f"No nearby '{place_type}' places found within {radius_meters}m."

            results = []
            for place in places:
                display_name = place.get("displayName", {}).get("text", "")
                formatted_address = place.get("formattedAddress", "")
                loc = place.get("location", {})
                results.append({
                    "name": display_name,
                    "address": formatted_address,
                    "location": {
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude")
                    }
                })
            return str(results)
    except Exception as e:
        return f"Places API error: {e}"


# Configure A2UI v0.8 Schema Manager and Basic Catalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are Smart Pantry Recipe Concierge, a helpful AI culinary assistant. "
        "CRITICAL INSTRUCTION: You MUST pay close attention to any user allergies, dietary restrictions, or food sensitivities mentioned. "
        "Always remember user allergies across conversations using your Memory Bank tools (LoadMemoryTool and PreloadMemoryTool). "
        "When suggesting or recommending recipes, meals, or ingredients, you MUST strictly check for stored user allergies and guarantee that no suggested dish contains forbidden allergens. "
        "You help users discover recipes in their local pantry (via Firestore) as well as search for online meal ideas (via TheMealDB), "
        "look up full recipe details, find nearby grocery stores or food markets using Geocoding and Places (New) APIs, "
        "generate realistic dish photos using gemini-3.1-flash-lite-image, execute Python code safely in a sandbox, "
        "and add new recipes to their digital pantry using your tools."
    ),
    workflow_description="Analyze the user request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    tools=[
        search_recipes,
        get_recipe,
        add_recipe,
        generate_recipe_image,
        generate_item_image,
        generate_item_video,
        fetch_online_meal_ideas,
        geocode_address,
        find_nearby_places,
        LoadMemoryTool(),
        PreloadMemoryTool(),
    ],
    code_executor=get_code_executor(),
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
