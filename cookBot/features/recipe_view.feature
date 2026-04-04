Feature: Recipe View Page
  As a user of the recipe app
  I want to view a recipe's ingredients and steps
  So that I can follow along while cooking

  Background:
    Given a user exists with username "testchef" and password "testpass123"
    And that user has a recipe titled "Scrambled Eggs" with the following steps:
      | order | text                              |
      | 1     | Crack the eggs into a bowl        |
      | 2     | Whisk the eggs with a fork        |
      | 3     | Pour into a pan over medium heat  |
    And that recipe has the following ingredients:
      | name  | quantity | unit   |
      | eggs  | 3        | cup    |
      | butter| 1        | tbsp   |
      | salt  | 1        | tsp  |
    And I am logged in as "testchef" with password "testpass123"

  Scenario: Page loads and displays the recipe title
    When I visit the recipe view page
    Then I should see the heading "Scrambled Eggs"

  Scenario: Page displays all ingredients
    When I visit the recipe view page
    Then I should see "3 cup eggs" on the page
    And I should see "1 tbsp butter" on the page
    And I should see "1 tsp salt" on the page

  Scenario: Page displays all steps
    When I visit the recipe view page
    Then I should see "Crack the eggs into a bowl" on the page
    And I should see "Whisk the eggs with a fork" on the page
    And I should see "Pour into a pan over medium heat" on the page

  Scenario: Page returns 200 status for the recipe owner
    When I visit the recipe view page
    Then the page should load successfully
