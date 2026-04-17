Feature: Kroger store finder for missing ingredients

  Scenario: Unauthenticated user cannot access the store finder
    Given I am not logged in
    When I request nearby Kroger stores for a missing ingredient
    Then I should be redirected to the sign in page

  Scenario: Store finder requires location data
    Given I am a logged in user viewing a recipe with missing ingredients
    When I request nearby stores without providing a location
    Then I should receive a 400 error response

  Scenario: Store finder requires an ingredient
    Given I am a logged in user viewing a recipe with missing ingredients
    When I request nearby stores without providing an ingredient
    Then I should receive a 400 error response

  Scenario: User can find nearby stores for a missing ingredient
    Given I am a logged in user viewing a recipe with missing ingredients
    When I request nearby Kroger stores with a valid location and ingredient
    Then I should receive a 200 response with a list of nearby stores

  Scenario: Each store in the response has the required fields
    Given I am a logged in user viewing a recipe with missing ingredients
    When I request nearby Kroger stores with a valid location and ingredient
    Then each store should have a name, address, and distance

  Scenario: No stores found near the user returns an empty list
    Given I am a logged in user viewing a recipe with missing ingredients
    When I request nearby Kroger stores in a remote location
    Then I should receive a 200 response with an empty store list

  Scenario: Kroger API failure is handled gracefully
    Given I am a logged in user viewing a recipe with missing ingredients
    When the Kroger API is unavailable
    Then I should receive a 502 error response

  Scenario: Recipe page serves ingredients as objects for the JS renderer
    Given I am a logged in user viewing a recipe with missing ingredients
    When I load the recipe detail page
    Then each ingredient should have a display field and a name field

  Scenario: Recipe page serves pantry names for JS matching
    Given I am a logged in user with saffron in their pantry viewing a recipe with saffron
    When I load the recipe detail page
    Then the pantry names should include saffron

  Scenario: Pantry names are lowercased for JS comparison
    Given I am a logged in user with Saffron stored with a capital S
    When I load the recipe detail page
    Then the pantry names should contain saffron in lowercase