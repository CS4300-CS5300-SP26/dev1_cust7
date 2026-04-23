from behave import given, when, then
from django.contrib.auth.models import User
from home.models import Recipe, RecipeStep, RecipeIngredient, Tag, RecipeTag

# ── Given steps ──


@given('a user exists with username "{username}" and password "{password}"')
def step_create_user(context, username, password):
    user, _ = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.save()
    if not hasattr(context, "users"):
        context.users = {}
    context.users[username] = user


@given('a second user exists with username "{username}" and password "{password}"')
def step_create_second_user(context, username, password):
    step_create_user(context, username, password)


@given('that user has a recipe titled "{title}" with the following steps')
def step_create_recipe_with_steps(context, title):
    owner = list(context.users.values())[0]
    Recipe.objects.filter(title=title, user=owner).delete()
    recipe = Recipe.objects.create(title=title, user=owner, is_public=False)
    context.recipe = recipe
    for row in context.table:
        RecipeStep.objects.create(
            recipe=recipe, order=int(row["order"]), text=row["text"]
        )


@given("that recipe has the following ingredients")
def step_create_ingredients(context):
    for row in context.table:
        unit = row["unit"].strip() or None
        RecipeIngredient.objects.get_or_create(
            recipe=context.recipe,
            name=row["name"],
            defaults={
                "quantity": row["quantity"],
                "unit": unit,
            },
        )


@given('I am logged in as "{username}" with password "{password}"')
def step_login(context, username, password):
    user, _ = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.save()
    logged_in = context.client.login(username=username, password=password)
    assert logged_in, f"Login failed for user '{username}' with password '{password}'"
    context.user = user


@given('the recipe "{title}" is set to public')
def step_make_recipe_public(context, title):
    Recipe.objects.filter(title=title).update(is_public=True)
    context.recipe.refresh_from_db()


@given('a tag named "{name}" of type "{tag_type}" exists')
def step_create_tag(context, name, tag_type):
    tag, _ = Tag.objects.get_or_create(name=name, defaults={"tag_type": tag_type})
    if not hasattr(context, "tag_store"):
        context.tag_store = {}
    context.tag_store[name] = tag


@given('the recipe "{title}" has a tag named "{name}" of type "{tag_type}"')
def step_add_tag_to_recipe(context, title, name, tag_type):
    tag, _ = Tag.objects.get_or_create(name=name, defaults={"tag_type": tag_type})
    recipe = Recipe.objects.get(title=title)
    RecipeTag.objects.get_or_create(recipe=recipe, tag=tag)
    if not hasattr(context, "tag_store"):
        context.tag_store = {}
    context.tag_store[name] = tag


# ── When steps ──


@when("I visit the recipe view page")
def step_visit_recipe_page(context):
    context.response = context.client.get(f"/recipe/{context.recipe.id}/")


@when("I visit the create recipe page")
def step_visit_create_page(context):
    context.response = context.client.get("/recipe/create/")


@when("I visit the edit recipe page")
def step_visit_edit_page(context):
    context.response = context.client.get(f"/recipe/{context.recipe.id}/edit/")


@when('I submit a new recipe with title "{title}"')
def step_submit_new_recipe(context, title):
    context.last_post_data = {
        "title": title,
        "is_public": "",
        "ingredient_quantity[]": ["2"],
        "ingredient_unit[]": ["cups"],
        "ingredient_name[]": ["flour"],
        "steps[]": ["Mix everything together"],
        "tags[]": [],
    }
    context.response = context.client.post("/recipe/create/", context.last_post_data)


@when('I include the tag "{tag_name}" in the submission')
def step_include_tag_in_submission(context, tag_name):
    tag = Tag.objects.get(name=tag_name)
    Recipe.objects.filter(
        title=context.last_post_data["title"], user=context.user
    ).delete()
    context.last_post_data["tags[]"] = [str(tag.id)]
    context.response = context.client.post("/recipe/create/", context.last_post_data)


@when("I submit a new recipe with no title")
def step_submit_new_recipe_no_title(context):
    context.response = context.client.post(
        "/recipe/create/",
        {
            "title": "",
            "is_public": "",
            "ingredient_quantity[]": ["2"],
            "ingredient_unit[]": ["cups"],
            "ingredient_name[]": ["flour"],
            "steps[]": ["Mix everything together"],
        },
    )


@when('I submit an edit to the recipe changing the title to "{title}"')
def step_submit_edit_title(context, title):
    context.response = context.client.post(
        f"/recipe/{context.recipe.id}/edit/",
        {
            "title": title,
            "is_public": "",
            "ingredient_quantity[]": ["3"],
            "ingredient_unit[]": ["cup"],
            "ingredient_name[]": ["eggs"],
            "steps[]": ["Crack the eggs into a bowl", "Whisk the eggs with a fork"],
            "tags[]": [],
        },
    )


@when("I submit an edit to the recipe with no title")
def step_submit_edit_no_title(context):
    context.response = context.client.post(
        f"/recipe/{context.recipe.id}/edit/",
        {
            "title": "",
            "is_public": "",
            "ingredient_quantity[]": ["3"],
            "ingredient_unit[]": ["cup"],
            "ingredient_name[]": ["eggs"],
            "steps[]": ["Crack the eggs into a bowl"],
        },
    )


@when('I submit an edit to the recipe adding the tag "{tag_name}"')
def step_submit_edit_add_tag(context, tag_name):
    tag = Tag.objects.get(name=tag_name)
    context.response = context.client.post(
        f"/recipe/{context.recipe.id}/edit/",
        {
            "title": context.recipe.title,
            "is_public": "",
            "ingredient_quantity[]": ["3"],
            "ingredient_unit[]": ["cup"],
            "ingredient_name[]": ["eggs"],
            "steps[]": ["Crack the eggs into a bowl"],
            "tags[]": [str(tag.id)],
        },
    )


@when("I submit an edit to the recipe removing all tags")
def step_submit_edit_remove_tags(context):
    context.response = context.client.post(
        f"/recipe/{context.recipe.id}/edit/",
        {
            "title": context.recipe.title,
            "is_public": "",
            "ingredient_quantity[]": ["3"],
            "ingredient_unit[]": ["cup"],
            "ingredient_name[]": ["eggs"],
            "steps[]": ["Crack the eggs into a bowl"],
        },
    )


# ── Then steps ──


@then("the page should load successfully")
def step_page_loads(context):
    assert (
        context.response.status_code == 200
    ), f"Expected status 200 but got {context.response.status_code}"


@then("the response status should be {status_code:d}")
def step_check_status(context, status_code):
    assert (
        context.response.status_code == status_code
    ), f"Expected status {status_code} but got {context.response.status_code}"


@then('I should see the heading "{text}"')
def step_see_heading(context, text):
    content = context.response.content.decode("utf-8")
    assert (
        f"<h1>{text}</h1>" in content
    ), f"Could not find heading '<h1>{text}</h1>' in page content"


@then('I should see "{text}" on the page')
def step_see_text(context, text):
    content = context.response.content.decode("utf-8")
    assert text in content, f"Could not find '{text}' anywhere in the page content"


@then('I should not see "{text}" on the page')
def step_not_see_text(context, text):
    content = context.response.content.decode("utf-8")
    assert (
        text not in content
    ), f"Found '{text}' in page content but expected it to be absent"


@then('a recipe titled "{title}" should exist in the database')
def step_recipe_exists(context, title):
    exists = Recipe.objects.filter(title=title).exists()
    assert exists, f"No recipe with title '{title}' found in the database"


@then('the recipe "{title}" should have the tag "{tag_name}"')
def step_recipe_has_tag(context, title, tag_name):
    recipe = Recipe.objects.filter(title=title).last()
    assert recipe is not None, f"No recipe with title '{title}' found"
    has_tag = recipe.tags.filter(name=tag_name).exists()
    assert has_tag, f"Recipe '{title}' does not have tag '{tag_name}'"


@then('the recipe "{title}" should have no tags')
def step_recipe_has_no_tags(context, title):
    recipe = Recipe.objects.filter(title=title).last()
    assert recipe is not None, f"No recipe with title '{title}' found"
    count = recipe.tags.count()
    assert count == 0, f"Recipe '{title}' still has {count} tag(s)"
