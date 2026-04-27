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

  Scenario: User saves all meals to My Recipes successfully
    Given I am a logged-in user with a generated meal plan
    When I click save all meals to my recipes
    Then all meals should be saved as private recipes
    And I should receive a success message with saved count

  Scenario: User tries to save with no meal plan generated
    Given I am a logged-in user
    When I click save all meals to my recipes
    Then I should see a warning message "No meal found"

  Scenario: Unauthenticated user cannot save meal plan
    Given I am a logged-out user
    When I click save all meals to my recipes
    Then I should be redirected when trying to save

  Scenario: Saving twice does not create duplicate recipes
    Given I am a logged-in user with a generated meal plan
    When I click save all meals to my recipes
    And I click save all meals to my recipes again
    Then I should see a warning message about already saved

  Scenario: Saved meal recipes are private by default
    Given I am a logged-in user with a generated meal plan
    When I click save all meals to my recipes
    Then all saved meal recipes should be private

  Scenario: Saved meal recipes include macro information in description
    Given I am a logged-in user with a generated meal plan
    When I click save all meals to my recipes
    Then the saved recipes should include macro information
