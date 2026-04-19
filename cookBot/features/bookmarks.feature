Feature: Recipe Bookmark
  As a home cook,
  I want to be able to save recipes I enjoy
  So that I can easily find them again.

  Scenario: Successfully bookmarking and un-bookmarking a recipe
    Given I am a logged in user and a recipe exists
    When I click the bookmark icon for the recipe
    Then the icon should change state and the recipe is saved
    And the recipe appears on the "Saved Recipes" page
    When I click the bookmark icon again
    Then the recipe is removed from the "Saved Recipes" page
