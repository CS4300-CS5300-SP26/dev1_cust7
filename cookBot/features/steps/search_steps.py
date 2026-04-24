from behave import given, when
from home.models import Recipe, Tag, RecipeTag

# ── Search given steps ──


@given('"{username}" has a public recipe titled "{title}"')
def step_user_has_public_recipe(context, username, title):
    user = context.users[username]
    recipe = Recipe.objects.create(user=user, title=title, is_public=True)
    if not hasattr(context, "recipes"):
        context.recipes = {}
    context.recipes[title] = recipe


@given('"{username}" has a private recipe titled "{title}"')
def step_user_has_private_recipe(context, username, title):
    user = context.users[username]
    recipe = Recipe.objects.create(user=user, title=title, is_public=False)
    if not hasattr(context, "recipes"):
        context.recipes = {}
    context.recipes[title] = recipe


@given('the recipe "{title}" has the tag "{tag_name}"')
def step_recipe_has_tag_by_name(context, title, tag_name):
    recipe = Recipe.objects.get(title=title)
    tag = Tag.objects.get(name=tag_name)
    RecipeTag.objects.get_or_create(recipe=recipe, tag=tag)


# ── Search when steps ──


@when("I visit the search page")
def step_visit_search_page(context):
    context.response = context.client.get("/search/")


@when("I visit the home page")
def step_visit_home_page(context):
    context.response = context.client.get("/")


@when('I filter by the tag "{tag_name}"')
def step_filter_by_tag(context, tag_name):
    tag = Tag.objects.get(name=tag_name)
    # Accumulate tag ids across multiple filter steps
    if not hasattr(context, "active_tag_ids"):
        context.active_tag_ids = []
    context.active_tag_ids.append(tag.id)
    context.response = context.client.get("/search/", {"tags": context.active_tag_ids})


@when('I search for "{query}" and filter by the tag "{tag_name}"')
def step_search_and_filter(context, query, tag_name):
    tag = Tag.objects.get(name=tag_name)
    context.response = context.client.get("/search/", {"q": query, "tags": [tag.id]})


@when('I search for "{query}"')
def step_search_for(context, query):
    context.response = context.client.get("/search/", {"q": query})
