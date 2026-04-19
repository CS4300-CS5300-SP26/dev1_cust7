Feature: Recipe Comments
  As a home cook
  I want to be able to leave comments on recipes
  So that I can share feedback and tips with other cooks

  Scenario: Successfully posting a comment on a recipe
    Given I am logged in and viewing a recipe
    When I submit a comment with text "This recipe turned out perfect!"
    Then the comment should be saved to the database
    And the comment should be associated with the recipe
    And the comment should be associated with my user account

  Scenario: Cannot post comment when not logged in
    Given I am not logged in
    When I submit a comment with text "Great recipe!"
    Then no comment should be created