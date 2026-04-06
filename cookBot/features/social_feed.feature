Feature: Social feed

Scenario: Public recipe appears in the social feed
    Given a logged in user exists
    When I create a public recipe
    Then the recipe should appear in the social feed

Scenario: Private recipe does not appear in the social feed
    Given a logged in user exists
    When I create a private recipe
    Then the recipe should not appear in the social feed

Scenario: Making a recipe public shares it to the feed
    Given a logged in user exists
    When I create a private recipe and then make it public
    Then the recipe should appear in the social feed

Scenario: Making a recipe private removes it from the feed
    Given a logged in user exists
    When I create a public recipe and then make it private
    Then the recipe should not appear in the social feed

Scenario: Logged in user can view the social feed
    Given a logged in user exists
    When I visit the social feed page
    Then the page should load successfully

Scenario: Logged out user is redirected from the social feed
    Given a logged out user
    When I visit the social feed page
    Then I should be redirected

Scenario: Feed shows recipes from all users
    Given a logged in user exists
    When two different users share a recipe each
    Then both recipes should appear in the social feed

Scenario: Feed is ordered newest first
    Given a logged in user exists
    When I visit the social feed page with multiple public recipes
    Then the recipes should be ordered newest first

Scenario: Feed shows empty state when no recipes are shared
    Given a logged in user exists
    When no public recipes exist
    Then the feed should contain no recipes

Scenario: Feed links to the recipe page
    Given a logged in user exists
    When a public recipe exists in the feed
    Then the feed should link to that recipe's page