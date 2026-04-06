Feature: User Sign in

  Scenario: User can sign in
    Given a registered user exists
    When I submit valid sign in credentials
    Then I should be redirected to the home page
    And the user should be authenticated

  Scenario: User can sign out
    Given I am a logged in user
    When I visit the logout page
    Then I should be redirected to the home page
    And the user should not be authenticated