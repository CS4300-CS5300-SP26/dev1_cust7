Feature: Recipe Search 

    Scenario: Search recipes with empty pantry
        Given I am a logged in user
        When I search for recipes by pantry
        Then I should see the message "No ingredients in pantry"

  Scenario: Search recipes with ingredients
        Given I am a logged in user
        And "Chicken" is already in my pantry
        When I search for recipes by pantry
        Then I should receive at least one recipe result

  Scenario: Fallback recipes when API is unavailable
        Given I am a logged in user
        And "Potato" is already in my pantry
        When I request fallback recipes
        Then I should still receive recipe suggestions