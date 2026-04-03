Feature: Meal Calendar Management

  Scenario: Generate meals with ingredients (Happy Path)
    Given I am a logged-in user
    And I have "Chicken" and "Pasta" in my pantry
    When I click "Generate Weekly Plan"
    Then I should see 7 meals on the calendar grid

  Scenario: Attempt generation with empty pantry (Edge Case)
    Given I am a logged-in user
    And my pantry is currently empty
    When I click "Generate Weekly Plan"
    Then I should see a warning message "Please add ingredients first"

  Scenario: Meal plan persists after page reload (Persistence Check)
    Given I am a logged-in user
    And I have "Chicken" and "Pasta" in my pantry
    And I have generated a weekly meal plan
    When I return to the calendar page
    Then the previously generated meals should still be visible