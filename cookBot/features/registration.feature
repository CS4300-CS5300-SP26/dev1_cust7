Feature: User Registration

      Scenario: User Registers successfully
            Given No user exists with username "newuser"
            And no user exists with email "newuser@email.com"
            When I submit valid registration details
            Then the registration should succeed
            And the user should be able to log in

      Scenario: User cannot register with a duplicate email
            Given a user exists with email "test@email.com"
            When I submit registration details with "test@email.com"
            Then the registration should fail
            And I should see a duplicate email error

