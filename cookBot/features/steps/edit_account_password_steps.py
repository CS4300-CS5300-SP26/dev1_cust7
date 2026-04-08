from behave import given, when, then
from django.urls import reverse


@when("I submit a valid password change")
def step_submit_valid_password_change(context):
    context.response = context.client.post(
        "/account/change-password/",
        {
            "old_password": "testpass123",
            "new_password1": "NewStrongPassword123!",
            "new_password2": "NewStrongPassword123!",
        },
    )


@when("I submit a password change with the wrong current password")
def step_submit_invalid_old_password_change(context):
    context.response = context.client.post(
        "/account/change-password/",
        {
            "old_password": "wrongpassword",
            "new_password1": "NewStrongPassword123!",
            "new_password2": "NewStrongPassword123!",
        },
    )


@then("the password change should succeed")
def step_password_change_succeeds(context):
    assert context.response.status_code == 302


@then("I can log in with the new password")
def step_can_login_with_new_password(context):
    from django.test import Client

    client = Client()
    response = client.post(
        "/signin/",
        {
            "username": "testuser",
            "password": "NewStrongPassword123!",
        },
    )

    assert response.status_code == 302
    assert client.session.get("_auth_user_id") is not None


@then("I cannot log in with the old password")
def step_cannot_login_with_old_password(context):
    from django.test import Client

    client = Client()
    client.post(
        "/signin/",
        {
            "username": "testuser",
            "password": "testpass123",
        },
    )

    assert client.session.get("_auth_user_id") is None


@then("the password change should fail")
def step_password_change_fails(context):
    assert context.response.status_code == 200
