Feature: Recipe Search Page
  As a user of CookBot
  I want to search and filter public recipes
  So that I can find recipes I am interested in

  Background:
    Given a user exists with username "testchef" and password "testpass123"
    And a user exists with username "otherchef" and password "testpass123"
    And "testchef" has a public recipe titled "Vegan Pasta"
    And "testchef" has a public recipe titled "Chicken Soup"
    And "otherchef" has a public recipe titled "Scrambled Eggs"
    And "testchef" has a private recipe titled "Secret Stew"
    And a tag named "Vegan" of type "dietary" exists
    And a tag named "Italian" of type "cuisine" exists
    And the recipe "Vegan Pasta" has the tag "Vegan"
    And the recipe "Vegan Pasta" has the tag "Italian"

  Scenario: Search page loads successfully
    When I visit the search page
    Then the page should load successfully

  Scenario: Search page loads for unauthenticated users
    Given I am not logged in
    When I visit the search page
    Then the page should load successfully

  Scenario: All public recipes are shown by default
    When I visit the search page
    Then I should see "Vegan Pasta" on the page
    And I should see "Scrambled Eggs" on the page
    And I should see "Chicken Soup" on the page

  Scenario: Private recipes never appear in search results
    When I visit the search page
    Then I should not see "Secret Stew" on the page

  Scenario: Search by recipe title
    When I search for "pasta"
    Then I should see "Vegan Pasta" on the page
    And I should not see "Scrambled Eggs" on the page
    And I should not see "Chicken Soup" on the page

  Scenario: Search is case insensitive
    When I search for "PASTA"
    Then I should see "Vegan Pasta" on the page

  Scenario: Search by username
    When I search for "otherchef"
    Then I should see "Scrambled Eggs" on the page
    And I should not see "Vegan Pasta" on the page

  Scenario: Search with no matches shows no results message
    When I search for "xyznotarecipe"
    Then I should see "No recipes found" on the page

  Scenario: Filter by a single tag
    When I filter by the tag "Vegan"
    Then I should see "Vegan Pasta" on the page
    And I should not see "Scrambled Eggs" on the page
    And I should not see "Chicken Soup" on the page

  Scenario: Filter by multiple tags shows only recipes with all tags
    When I filter by the tag "Vegan"
    And I filter by the tag "Italian"
    Then I should see "Vegan Pasta" on the page
    And I should not see "Scrambled Eggs" on the page

  Scenario: Tag filter options are visible on the search page
    When I visit the search page
    Then I should see "Vegan" on the page
    And I should see "Italian" on the page

  Scenario: Search and tag filter can be combined
    When I search for "pasta" and filter by the tag "Vegan"
    Then I should see "Vegan Pasta" on the page
    And I should not see "Scrambled Eggs" on the page

  Scenario: Home page shows tags for browsing
    When I visit the home page
    Then I should see "Vegan" on the page
    And I should see "Italian" on the page