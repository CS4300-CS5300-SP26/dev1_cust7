Feature: Recipe star rating system

  Scenario: Logged out user cannot rate a recipe
    Given a public recipe exists
    When an unauthenticated user submits a rating of 4 for that recipe
    Then I should be redirected to the sign in page

  Scenario: Logged in user can rate a recipe
    Given a logged in user exists
    And a public recipe exists
    When the user submits a rating of 4 for that recipe
    Then the response should indicate success
    And the returned average should be 4.0
    And the returned count should be 1

  Scenario: User can rate their own recipe
    Given a logged in user exists
    And that user has created a public recipe
    When the user submits a rating of 3 for that recipe
    Then the response should indicate success
    And the returned count should be 1

  Scenario: Rating must be between 1 and 5
    Given a logged in user exists
    And a public recipe exists
    When the user submits a rating of 0 for that recipe
    Then I should receive a 400 error response
    When the user submits a rating of 6 for that recipe
    Then I should receive a 400 error response

  Scenario: User can change their rating but not submit a duplicate
    Given a logged in user exists
    And a public recipe exists
    When the user submits a rating of 2 for that recipe
    Then the returned count should be 1
    When the user submits a rating of 5 for that recipe
    Then the response should indicate success
    And the returned count should be 1
    And the returned average should be 5.0

  Scenario: Average rating reflects multiple users
    Given a logged in user exists
    And a public recipe exists
    And a second user has rated that recipe 2 stars
    When the user submits a rating of 4 for that recipe
    Then the returned average should be 3.0
    And the returned count should be 2

  Scenario: Rating a private recipe as a non-owner is forbidden
    Given a logged in user exists
    And another user has created a private recipe
    When the user submits a rating of 5 for that private recipe
    Then I should receive a 403 error response

  Scenario: Recipe view page shows the current user's existing rating
    Given a logged in user exists
    And a public recipe exists
    And the user has already rated that recipe 3 stars
    When the user visits the recipe view page
    Then the page should show 3 filled stars

  Scenario: Recipe view page shows the average rating
    Given a logged in user exists
    And a public recipe exists
    And a second user has rated that recipe 4 stars
    When the user visits the recipe view page
    Then the page should display the average rating