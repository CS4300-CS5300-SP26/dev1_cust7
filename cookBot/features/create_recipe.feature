Feature: Create Recipe Page
  As a logged-in user
  I want to create a new recipe
  So that I can save and share my cooking

  Background:
    Given a user exists with username "testchef" and password "testpass123"
    And I am logged in as "testchef" with password "testpass123"

  Scenario: Create recipe page loads successfully
    When I visit the create recipe page
    Then the page should load successfully

  Scenario: Unauthenticated user is redirected away from create page
    Given I am not logged in
    When I visit the create recipe page
    Then the response status should be 302

  Scenario: Submitting a valid recipe creates it and redirects
    When I submit a new recipe with title "Banana Bread"
    Then a recipe titled "Banana Bread" should exist in the database
    And the response status should be 302

  Scenario: Submitting a recipe with no title shows an error
    When I submit a new recipe with no title
    Then I should see "Title cannot be empty" on the page

  Scenario: Tag options are displayed on the create recipe page
    Given a tag named "Vegan" of type "dietary" exists
    When I visit the create recipe page
    Then I should see "Vegan" on the page

  Scenario: Tags from all categories are shown grouped on the create page
    Given a tag named "Vegan" of type "dietary" exists
    And a tag named "Italian" of type "cuisine" exists
    And a tag named "Breakfast" of type "meal" exists
    When I visit the create recipe page
    Then I should see "Vegan" on the page
    And I should see "Italian" on the page
    And I should see "Breakfast" on the page

  Scenario: Submitting a recipe with a tag links the tag to the recipe
    Given a tag named "Vegan" of type "dietary" exists
    When I submit a new recipe with title "Vegan Pasta"
    And I include the tag "Vegan" in the submission
    Then a recipe titled "Vegan Pasta" should exist in the database
    And the recipe "Vegan Pasta" should have the tag "Vegan"
