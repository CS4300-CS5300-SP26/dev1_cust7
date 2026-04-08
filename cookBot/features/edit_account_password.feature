Feature: Change Password
      Scenario: User changes password successfully
            Given I am a logged in user
            When I submit a valid password change
            Then the password change should succeed
            And I can log in with the new password
            And I cannot log in with the old password
      Scenario: User cannot change password with wrong current password
            Given I am a logged in user
            When I submit a password change with the wrong current password
            Then the password change should fail