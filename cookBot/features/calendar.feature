Feature: Meal Calendar Management

  Scenario: Generate meals with ingredients (Happy Path)
    Given I am a logged-in user
    And I have "Chicken" and "Pasta" in my pantry
    When I click "Generate Weekly Plan"
    Then I should see 21 meals on the calendar grid

  Scenario: Attempt generation with empty pantry (Edge Case)
    Given I am a logged-in user
    And my pantry is currently empty
    When I click "Generate Weekly Plan"
    Then I should see a warning message "Your pantry is empty"

  Scenario: Meal plan persists after page reload (Persistence Check)
    Given I am a logged-in user
    And I have "Chicken" and "Pasta" in my pantry
    And I have generated a weekly meal plan
    When I return to the calendar page
    Then the previously generated meals should still be visible
  
  Scenario: Generate meal plan with all fields and pantry on
    Given I am a logged-in user
    And I have "Chicken" and "Rice" in my pantry
    When I generate a meal plan with calories "500" protein "30" fat "15" carbs "50" cuisine "Italian" and pantry on
    Then I should see 21 meals on the calendar grid

  Scenario: Generate meal plan with all fields and pantry off
    Given I am a logged-in user
    When I generate a meal plan with calories "500" protein "30" fat "15" carbs "50" cuisine "Mexican" and pantry off
    Then I should see 21 meals on the calendar grid

  Scenario: Generate meal plan with all fields empty
    Given I am a logged-in user
    When I generate a meal plan with no inputs and pantry off
    Then I should see 21 meals on the calendar grid

  Scenario: Generate meal plan with only macros filled out
    Given I am a logged-in user
    When I generate a meal plan with calories "600" protein "40" fat "20" carbs "60" and no cuisine
    Then I should see 21 meals on the calendar grid

  Scenario: Generate meal plan with only cuisine filled out
    Given I am a logged-in user
    When I generate a meal plan with cuisine "Japanese" and no macros
    Then I should see 21 meals on the calendar grid

  Scenario: Generate meal plan with pantry on but pantry is empty
    Given I am a logged-in user
    And my pantry is currently empty
    When I generate a meal plan with pantry on and no other inputs
    Then I should see a warning message "Your pantry is empty"
