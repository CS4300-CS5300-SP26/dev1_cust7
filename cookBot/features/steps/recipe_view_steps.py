from behave import given, when, then
from django.contrib.auth.models import User
from home.models import Recipe, RecipeStep, RecipeIngredient


@given('a user exists with username "{username}" and password "{password}"')
def step_create_user(context, username, password):
    user, _ = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.save()
    # Store on context so other steps can find the user by username
    if not hasattr(context, "users"):
        context.users = {}
    context.users[username] = user


@given('that user has a recipe titled "{title}" with the following steps')
def step_create_recipe_with_steps(context, title):
    # The recipe belongs to the first user created in the background
    owner = list(context.users.values())[0]

    # Delete any existing recipe with this title to ensure test isolation
    Recipe.objects.filter(title=title, user=owner).delete()

    recipe = Recipe.objects.create(title=title, user=owner, is_public=False)
    context.recipe = recipe

    # Create each step row from the feature file table
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
    # Ensure user exists with the correct password
    user, created = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.save()

    logged_in = context.client.login(username=username, password=password)
    assert logged_in, f"Login failed for user '{username}' with password '{password}'"
    context.user = user


# When steps
@when("I visit the recipe view page")
def step_visit_recipe_page(context):
    url = f"/recipe/{context.recipe.id}/"
    context.response = context.client.get(url)


# Then steps
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


# user control tests
@given('a second user exists with username "{username}" and password "{password}"')
def step_create_second_user(context, username, password):
    step_create_user(context, username, password)


@given('the recipe "{title}" is set to public')
def step_make_recipe_public(context, title):
    Recipe.objects.filter(title=title).update(is_public=True)
    # Refresh context.recipe so it reflects the updated value
    context.recipe.refresh_from_db()
