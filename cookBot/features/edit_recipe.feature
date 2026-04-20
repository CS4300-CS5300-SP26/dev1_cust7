Feature: Edit Recipe Page
  As the owner of a recipe
  I want to edit my recipe
  So that I can keep it accurate and up to date

  Background:
    Given a user exists with username "testchef" and password "testpass123"
    And that user has a recipe titled "Scrambled Eggs" with the following steps
      | order | text                       |
      | 1     | Crack the eggs into a bowl |
      | 2     | Whisk the eggs with a fork |
    And that recipe has the following ingredients
      | name | quantity | unit |
      | eggs | 3        | cup  |
    And I am logged in as "testchef" with password "testpass123"

  Scenario: Edit recipe page loads successfully for the owner
    When I visit the edit recipe page
    Then the page should load successfully

  Scenario: Edit page is pre-populated with the existing recipe title
    When I visit the edit recipe page
    Then I should see "Scrambled Eggs" on the page

  Scenario: Edit page is pre-populated with existing ingredients
    When I visit the edit recipe page
    Then I should see "eggs" on the page

  Scenario: Edit page is pre-populated with existing steps
    When I visit the edit recipe page
    Then I should see "Crack the eggs into a bowl" on the page

  Scenario: A non-owner cannot access the edit page
    Given a second user exists with username "otheruser" and password "otherpass123"
    And I am logged in as "otheruser" with password "otherpass123"
    When I visit the edit recipe page
    Then the response status should be 403

  Scenario: Unauthenticated user is redirected away from edit page
    Given I am not logged in
    When I visit the edit recipe page
    Then the response status should be 302

  Scenario: Submitting the edit form updates the recipe title
    When I submit an edit to the recipe changing the title to "Fluffy Scrambled Eggs"
    Then a recipe titled "Fluffy Scrambled Eggs" should exist in the database
    And the response status should be 302

  Scenario: Submitting an empty title on edit shows an error
    When I submit an edit to the recipe with no title
    Then I should see "Title cannot be empty" on the page

  Scenario: Existing tags are pre-selected on the edit page
    Given the recipe "Scrambled Eggs" has a tag named "Breakfast" of type "meal"
    When I visit the edit recipe page
    Then I should see "Breakfast" on the page

  Scenario: Editing a recipe can add a new tag
    Given a tag named "Vegetarian" of type "dietary" exists
    When I submit an edit to the recipe adding the tag "Vegetarian"
    Then the recipe "Scrambled Eggs" should have the tag "Vegetarian"

  Scenario: Editing a recipe can remove an existing tag
    Given the recipe "Scrambled Eggs" has a tag named "Breakfast" of type "meal"
    When I submit an edit to the recipe removing all tags
    Then the recipe "Scrambled Eggs" should have no tags