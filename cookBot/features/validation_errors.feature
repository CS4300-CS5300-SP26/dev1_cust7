Feature: Form Validation Errors
  As a user
  I want to see validation errors when I enter invalid data
  So that I can correct my input

  Scenario: User tries to register with mismatched passwords
    Given I am on the register page
    When I fill in the registration form with:
      | field       | value                |
      | first_name  | Test                 |
      | last_name   | User                 |
      | username    | testvalidationuser   |
      | email       | testval@test.com     |
      | password1   | StrongPassword123!   |
      | password2   | DifferentPassword1!  |
    And I submit the registration form
    Then I should see a password mismatch error

  Scenario: User tries to register with existing username
    Given I am on the register page
    When I fill in the registration form with:
      | field       | value                |
      | username    | testuser             |
      | password1   | StrongPassword123!   |
      | password2   | StrongPassword123!   |
    And I submit the registration form
    Then I should see a username already exists error

  Scenario: User tries to save a recipe without a title
    Given I am logged in as "testuser" with password "password123"
    When I navigate to the create recipe page
    And I submit the recipe form without a title
    Then I should see an error message about the title

  Scenario: User tries to change email to one already in use
    Given I am logged in as "testuser" with password "password123"
    And another user exists with email "taken@email.com"
    When I navigate to the edit account page
    And I change my email to "taken@email.com"
    And I submit the edit account form
    Then I should see an email already in use error

  Scenario: User tries to add duplicate ingredient to pantry
    Given I am logged in as "testuser" with password "password123"
    And "Chicken" is in my pantry
    When I navigate to the pantry page
    And I try to add "Chicken" to my pantry
    Then I should see a duplicate ingredient error

  Scenario: User enters invalid characters in username during registration
    Given I am on the register page
    When I fill in the registration form with:
      | field       | value                |
      | username    | test@user!           |
      | password1   | StrongPassword123!   |
      | password2   | StrongPassword123!   |
    And I submit the registration form
    Then I should see a username validation error