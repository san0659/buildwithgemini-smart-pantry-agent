import os
from google.cloud import firestore

# CRITICAL: Hardcode the GCP Project ID string. Do NOT use GOOGLE_CLOUD_PROJECT
# or google.auth.default() as those return the project NUMBER when deployed.
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-c421a42d4a54"

def seed_database():
    print(f"Connecting to Firestore for project: {FIRESTORE_PROJECT_ID}...")
    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    
    recipes_ref = db.collection("recipes")
    
    sample_recipes = [
        {
            "recipe_id": "spaghetti-carbonara",
            "title": "Classic Spaghetti Carbonara",
            "cuisine": "Italian",
            "prep_time_minutes": 20,
            "servings": 2,
            "ingredients": ["spaghetti", "eggs", "pancetta", "parmesan cheese", "black pepper"],
            "instructions": [
                "Boil spaghetti in salted water until al dente.",
                "Sauté pancetta in a pan until crispy.",
                "Whisk eggs and grated parmesan together in a bowl.",
                "Toss hot pasta with pancetta, remove from heat, and quickly stir in egg mixture to form a creamy sauce."
            ],
            "dietary_tags": ["quick", "high-protein"]
        },
        {
            "recipe_id": "avocado-egg-toast",
            "title": "Avocado & Poached Egg Toast",
            "cuisine": "American",
            "prep_time_minutes": 10,
            "servings": 1,
            "ingredients": ["sourdough bread", "avocado", "eggs", "red pepper flakes", "lemon juice", "salt"],
            "instructions": [
                "Toast the sourdough bread until golden and crisp.",
                "Mash avocado with lemon juice, salt, and red pepper flakes.",
                "Poach egg in simmering water for 3 minutes.",
                "Spread mashed avocado on toast and top with the poached egg."
            ],
            "dietary_tags": ["vegetarian", "breakfast", "quick"]
        },
        {
            "recipe_id": "garlic-chicken-stirfry",
            "title": "Garlic Chicken & Vegetable Stir-Fry",
            "cuisine": "Asian",
            "prep_time_minutes": 25,
            "servings": 3,
            "ingredients": ["chicken breast", "broccoli", "bell pepper", "soy sauce", "garlic", "ginger", "sesame oil"],
            "instructions": [
                "Slice chicken breast into thin strips.",
                "Heat sesame oil in a wok and stir-fry minced garlic and ginger.",
                "Add chicken strips and cook until browned.",
                "Add broccoli florets and bell peppers with soy sauce, cooking until veggies are tender-crisp."
            ],
            "dietary_tags": ["dairy-free", "high-protein", "healthy"]
        },
        {
            "recipe_id": "berry-smoothie-bowl",
            "title": "Acai & Mixed Berry Smoothie Bowl",
            "cuisine": "Contemporary",
            "prep_time_minutes": 5,
            "servings": 1,
            "ingredients": ["frozen acai packet", "frozen berries", "banana", "almond milk", "granola", "chia seeds"],
            "instructions": [
                "Blend frozen acai, berries, banana, and almond milk until thick and smooth.",
                "Pour into a bowl.",
                "Top with crunchy granola, fresh berries, and chia seeds."
            ],
            "dietary_tags": ["vegan", "gluten-free", "breakfast"]
        }
    ]

    for recipe in sample_recipes:
        doc_ref = recipes_ref.document(recipe["recipe_id"])
        doc_ref.set(recipe)
        print(f"Seeded recipe: {recipe['title']} (ID: {recipe['recipe_id']})")

    print("\nFirestore seeding complete!")

if __name__ == "__main__":
    seed_database()
