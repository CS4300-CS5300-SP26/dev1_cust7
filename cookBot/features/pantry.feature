Feature: Pantry Management

    Scenario: User can view their pantry
        Given I am a logged in user
        When I visit the pantry page
        Then the pantry page should load successfully

    Scenario: User can add an ingredient
        Given I am a logged in user
        When I add the ingredient "Carrot" to my pantry
        Then "Carrot" should exist in the pantry

    Scenario: User cannot add a duplicate ingredient
        Given I am a logged in user
        And "Apple" is already in my pantry
        When I add the ingredient "Apple" to my pantry
        Then I should receive a 400 error response

    Scenario: User can delete an ingredient
        Given I am a logged in user
        And "Onion" is already in my pantry
        When I delete "Onion" from my pantry
        Then "Onion" should not exist in the pantry 