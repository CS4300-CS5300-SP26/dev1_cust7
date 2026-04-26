Feature: Meal Plan History
  As a logged-in user,
  I want to view a history of my saved meal plans
  So that I can revisit and manage past plans.

  Scenario: User sees empty history
    Given I am a logged-in user
    And I have no saved meal plans
    When I go to the meal plan history page
    Then I should see "No Meal Plan History"

  Scenario: User sees populated history
    Given I am a logged-in user
    And I have 3 saved meal plans
    When I go to the meal plan history page
    Then I should see 3 meal plans listed with their creation dates

  Scenario: Navigation
    Given I am a logged-in user
    And I have 3 saved meal plans
    When I go to the meal plan history page
    And I click on the first meal plan in the history
    Then I should be on the view page for that meal plan
