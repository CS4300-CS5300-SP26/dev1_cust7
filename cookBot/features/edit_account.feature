Feature: Edit account details
      Scenario: User updates account details successfully
            Given I am a logged in user
            When I submit valid account changes
            Then the account update should succeed
            And my first name should be updated
            And my email should be updated
      Scenario: User cannot change email to one already in use
            Given I am a logged in user
            And another user exists with email "taken@email.com"
            When I submit account changes with email "taken@email.com"
            Then the account update should fail
            And I should see the email already in use error
