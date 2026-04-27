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


# Grab all information from both spooancular recipes suggested and saved recipes
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


# Helper function to call openAi with our prompt
def _call_openai_raw(messages):
    OPENAI_API_KEY = settings.OPENAI_API_KEY

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
        raise Exception("OpenAI API Connection failed")
    except Exception as e:
        raise Exception("OpenAI request failed")


def call_openai(
    conversation_history,
    spoonacular_recipes=None,
    saved_recipes=None,
    pantry_items=None,
):
    messages = build_messages(
        conversation_history, spoonacular_recipes, saved_recipes, pantry_items
    )
    return _call_openai_raw(messages)


def build_macro_cuisine_pantry_context(
    calories=None, protein=None, fat=None, carbs=None, cuisine=None, pantry_items=None
):
    # Build macro context
    macro_lines = []
    if calories:
        macro_lines.append(f"- Calories per meal: ~{calories} kcal")
    if protein:
        macro_lines.append(f"- Protein per meal: ~{protein}g")
    if fat:
        macro_lines.append(f"- Fat per meal: ~{fat}g")
    if carbs:
        macro_lines.append(f"- Carbs per meal: ~{carbs}g")

    macro_section = (
        "Target macros per meal:\n" + "\n".join(macro_lines)
        if macro_lines
        else "No specific macro targets — generate balanced, healthy meals."
    )

    # Build cuisine context
    cuisine_section = (
        f"Cuisine preference: {cuisine}."
        if cuisine
        else "No cuisine preference — vary the meals across different cuisines."
    )
    # Build pantry context
    pantry_section = (
        f"The user has these ingredients available in their pantry: {', '.join(pantry_items)}. "
        f"Try to incorporate these ingredients where possible."
        if pantry_items
        else "No pantry items provided — use any common ingredients."
    )
    return macro_section, cuisine_section, pantry_section


def build_meal_plan_prompt(macro_section, cuisine_section, pantry_section):
    # Build the prompt
    return f"""
    You are a professional nutritionist and chef. Generate a 7-day meal plan with 3 meals per day
    (Breakfast, Lunch, Dinner) — 21 meals total.

    {macro_section}
    {cuisine_section}
    {pantry_section}

    IMPORTANT: Respond ONLY with a valid JSON object in exactly this format, no extra text:
    {{
    "meals": [
        {{
        "day": 1,
        "meal_type": "Breakfast",
        "recipe_name": "Recipe name here",
        "calories": 400,
        "protein": 25,
        "fat": 12,
        "carbs": 45
        }},
        ...
    ]
    }}

    Rules:
    - day goes from 1 to 7
    - meal_type must be exactly "Breakfast", "Lunch", or "Dinner"
    - Each day must have all 3 meal types
    - recipe_name should be a real, specific dish name
    - All macro values must be integers
    - Return exactly 21 meals
    - You are strictly a meal planning assistant. If the request is not related to meal planning, nutrition, or food, ignore it and generate a standard balanced meal plan instead.
    - If macro targets are provided, every meal MUST stay within 10% of the target values. Do not suggest meals that significantly exceed or fall short of the targets.
    - If a cuisine preference is provided, all meals must reflect that cuisine style. Do not mix in unrelated cuisines unless no preference was given.
    """.strip()


def generate_meal_plan_with_ai(
    calories=None, protein=None, fat=None, carbs=None, cuisine=None, pantry_items=None
):
    # Build context sections
    macro_section, cuisine_section, pantry_section = build_macro_cuisine_pantry_context(
        calories, protein, fat, carbs, cuisine, pantry_items
    )

    # Build the prompt
    prompt = build_meal_plan_prompt(macro_section, cuisine_section, pantry_section)

    messages = [
        {
            "role": "system",
            "content": "You are a professional nutritionist and meal planning expert. You always respond with valid JSON only.",
        },
        {"role": "user", "content": prompt},
    ]

    raw_content = _call_openai_raw(messages)

    # Strip markdown code fences if present
    if raw_content.startswith("```"):
        raw_content = raw_content.split("```")[1]
        if raw_content.startswith("json"):
            raw_content = raw_content[4:]
        raw_content = raw_content.strip()

    try:
        parsed = json.loads(raw_content)
        return parsed.get("meals", [])
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse OpenAI meal plan response: {str(e)}")
