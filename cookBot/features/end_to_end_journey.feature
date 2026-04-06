Feature: End-to-End User Journey
  As a new user
  I want to go from login to meal planning
  So that I can experience the full workflow

  Scenario: Complete user journey from login to calendar
    Given I am on the sign in page
    When I log in with valid credentials
      | username  | password     |
      | testuser  | password123  |
    Then I should see the home page

    When I navigate to the pantry page
    And I add "Chicken" to my pantry
    And I add "Rice" to my pantry
    Then I should see both ingredients in my pantry

    When I navigate to the calendar page
    And I click the generate meal plan button
    Then I should see 7 meals on the calendar
    And the meals should be for the next 7 days

    When I navigate to the home page
    And I log out
    Then I should see the sign in page

  Scenario: User registers and creates their first recipe
    Given I am on the register page
    When I fill in the registration form with:
      | field       | value                  |
      | first_name  | New                    |
      | last_name   | RecipeUser             |
      | username    | newrecipeuser          |
      | email       | newrecipeuser@test.com |
      | password1   | StrongPassword123!     |
      | password2   | StrongPassword123!     |
    And I submit the registration form
    Then I should be redirected to the home page

    When I navigate to the create recipe page
    And I create a recipe titled "Test Omelette" with ingredients:
      | quantity | unit | name   |
      | 3        |      | eggs   |
      | 1        | tbsp | butter |
    And steps:
      | order | text                    |
      | 1     | Crack eggs into bowl    |
      | 2     | Whisk and cook in pan   |
    Then I should see the recipe view page
    And the recipe title should be "Test Omelette"

  Scenario: User searches for recipes based on pantry ingredients
    Given I am logged in as "testuser" with password "password123"
    And "Chicken" is already in my pantry
    And "Rice" is already in my pantry
    When I navigate to the pantry page
    And I click search recipes
    Then I should see recipe suggestions
    And the recipes should use my pantry ingredients