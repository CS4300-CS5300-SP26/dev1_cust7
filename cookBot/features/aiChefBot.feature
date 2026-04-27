Feature: AI ChefBot chat functionality

  Scenario: Unauthenticated user cannot access aiChefBot
    Given I am not logged in
    When I visit the aiChefBot page
    Then I should be redirected to the sign in page

  Scenario: User cannot send an empty message
    Given I am a logged in user with a chat session
    When I submit an empty message to the chat
    Then I should receive a 400 error response

  Scenario: User cannot send a message with an invalid session ID
    Given I am a logged in user with a chat session
    When I submit a message with an invalid session ID
    Then I should receive a 404 error response

  Scenario: ChefBot handles an OpenAI API failure gracefully
    Given I am a logged in user with a chat session
    When the OpenAI API fails
    And I send a message
    Then I should receive a 500 error response

  Scenario: ChefBot page displays the user's saved recipes
    Given I am a logged in user with saved recipes
    When I visit the aiChefBot page with mocked Spoonacular
    Then I should see my saved recipes on the page

  Scenario: ChefBot page displays Spoonacular pantry matched recipes
    Given I am a logged in user with pantry ingredients
    When I visit the aiChefBot page with mocked Spoonacular
    Then I should see the Spoonacular suggested recipes on the page
  
  Scenario: ChefBot successfully responds to a user message
    Given I am a logged in user with a chat session
    When I send a valid message to ChefBot
    Then I should receive a reply from ChefBot
    And the message and reply should be saved to the database
  
  Scenario: ChefBot includes Spoonacular recipes in its context
    Given I am a logged in user with a chat session with Spoonacular context
    When I send a valid message to ChefBot
    Then the OpenAI call should include Spoonacular recipe context

  Scenario: ChefBot includes saved recipes in its context
    Given I am a logged in user with a chat session and saved recipes
    When I send a valid message to ChefBot
    Then the OpenAI call should include saved recipe context

  Scenario: ChefBot builds the correct message structure for OpenAI
    Given I am a logged in user with a chat session
    When I send a valid message to ChefBot
    Then the OpenAI call should have the system prompt as the first message

  Scenario: collect_context_from_recipes formats Spoonacular recipes correctly
    Given I have Spoonacular recipes
    When I collect context from those recipes
    Then the context should contain the Spoonacular recipe titles

  Scenario: collect_context_from_recipes formats saved recipes correctly
    Given I have saved recipe data
    When I collect context from those recipes
    Then the context should contain the saved recipe titles

  Scenario: collect_context_from_recipes returns empty string with no recipes
    Given I have no recipe data
    When I collect context from those recipes
    Then the context should be empty

  Scenario: build_messages puts system prompt first
    Given I have a conversation history
    When I build messages for OpenAI
    Then the first message should be the system prompt

  Scenario: build_messages injects recipe context into system prompt
    Given I have Spoonacular recipes
    When I build messages with that recipe context
    Then the system prompt should contain the recipe context

  Scenario: call_openai raises an exception on API failure
    Given I have a conversation history
    When the OpenAI API returns an error
    Then an exception should be raised with the error details

  Scenario: User saves a recipe from ChefBot successfully
    Given I am a logged in user with a chat session and a recipe response
    When I click save recipe
    Then the recipe should be saved to my recipes
    And I should receive a success response with the recipe title

  Scenario: User tries to save with no ChefBot response yet
    Given I am a logged in user with a chat session
    When I click save recipe
    Then I should receive a 400 error saying no response found

  Scenario: User tries to save a cooking tip that is not a recipe
    Given I am a logged in user with a chat session and a tip response
    When I click save recipe with mocked not a recipe response
    Then I should receive a 400 error saying not a recipe

  Scenario: Unauthenticated user cannot save a recipe
    Given I am not logged in
    When I try to save a recipe without logging in
    Then I should be redirected to the sign in page

  Scenario: User cannot save from another user's session
    Given I am a logged in user with a chat session
    When I try to save a recipe from another users session
    Then I should receive a 404 error response

  Scenario: Save recipe with invalid session ID
    Given I am a logged in user with a chat session
    When I try to save a recipe with an invalid session ID
    Then I should receive a 404 error response

  Scenario: Saved recipe is private by default
    Given I am a logged in user with a chat session and a recipe response
    When I click save recipe
    Then the saved recipe should be private

  Scenario: Saved recipe has correct ingredients and steps
    Given I am a logged in user with a chat session and a recipe response
    When I click save recipe
    Then the saved recipe should have ingredients and steps
