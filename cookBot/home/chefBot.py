import json
import urllib.request
import urllib.parse
from django.conf import settings

# AI prompt
SYSTEM_PROMPT = """
You are ChefBot, an expert culinary specialist and personal chef assistant for the CookBot app.
You have deep knowledge of cooking techniques, flavor profiles, cuisines from around the world,
and ingredient science.

Your core responsibilities:
1. Provide clear, detailed recipes with ingredients and step-by-step instructions when asked.
2. Proactively suggest ingredient substitutions — always offer alternatives for dietary
   restrictions, allergies, or simply what the user might have on hand.
3. Explain the "why" behind cooking techniques when helpful.
4. Stay focused on cooking and food-related topics only. Politely redirect off-topic questions.

When giving a recipe, always structure it as:
- Recipe name
- Brief description
- Ingredients (with quantities)
- Step-by-step instructions
- Suggested substitutions

When context about the user's saved recipes or Spoonacular recipe results is provided below,
reference them naturally. For example: "I can see you already have a Pasta Carbonara saved —
would you like tips on that, or a variation?"
""".strip()


# Grab all information from both Spoonacular suggested recipes and saved recipes
# So that the AI is aware of these
def collect_context_from_recipes(
    spoonacular_recipes=None, saved_recipes=None, pantry_items=None
):
    context = []

    # Grabbing spoonacular suggested recipes
    if spoonacular_recipes:
        spoon_lines = ["The user's pantry-matched recipes from Spoonacular:"]
        # Get only the first 5 to keep context manageable
        for r in spoonacular_recipes[:5]:
            used = ", ".join(r.get("used_ingredients", []))
            missed = ", ".join(r.get("missed_ingredients", []))
            spoon_lines.append(
                f"  - {r.get('title', 'Unknown')} "
                f"(uses: {used or 'N/A'}; missing: {missed or 'none'})"
            )
        context.append("\n".join(spoon_lines))

    # Grabbing saved recipes
    if saved_recipes:
        saved_lines = ["The user's personally saved recipes in CookBot:"]
        # Get only the first 10 to keep context manageable
        for r in saved_recipes[:10]:
            ingredients = ", ".join(
                f"{i.get('quantity', '')} {i.get('unit', '')} {i.get('name', '')}".strip()
                for i in r.get("ingredients", [])
            )
            saved_lines.append(
                f"  - {r.get('title', 'Unknown')} "
                f"(ingredients: {ingredients or 'not listed'})"
            )
        context.append("\n".join(saved_lines))
    # Grab pantry items
    if pantry_items:
        pantry_lines = ["The user currently has these ingredients in their pantry:"]
        pantry_lines.append(", ".join(pantry_items))
        context.append("\n".join(pantry_lines))

    return "\n\n".join(context)


# Combine the recipes pulled from spoonacular and saved and add it to our prompt
def build_messages(
    conversation_history,
    spoonacular_recipes=None,
    saved_recipes=None,
    pantry_items=None,
):
    system_content = SYSTEM_PROMPT

    context_block = collect_context_from_recipes(
        spoonacular_recipes, saved_recipes, pantry_items
    )
    if context_block:
        system_content += f"\n\n--- USER RECIPE CONTEXT ---\n{context_block}"

    messages = [{"role": "system", "content": system_content}]
    messages.extend(conversation_history)

    return messages


# Call openAi with our prompt along with the conversation history for a better response
def call_openai(
    conversation_history,
    spoonacular_recipes=None,
    saved_recipes=None,
    pantry_items=None,
):
    OPENAI_API_KEY = settings.OPENAI_API_KEY

    messages = build_messages(
        conversation_history, spoonacular_recipes, saved_recipes, pantry_items
    )

    payload = json.dumps(
        {
            "model": "gpt-5-mini",
            "messages": messages,
            "max_completion_tokens": 5000,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )
    # Implemented some error handling for failures
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"OpenAI API error {e.code}: {error_body}")
    except Exception as e:
        raise Exception(f"OpenAI request failed: {str(e)}")
