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