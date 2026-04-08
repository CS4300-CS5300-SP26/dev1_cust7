#!/usr/bin/env python3
import requests
import json

# Test the pantry functionality
base_url = "http://127.0.0.1:8000"


def test_pantry():
    """Test the complete pantry functionality"""
    session = requests.Session()

    print("=== Testing CookBot Pantry Functionality ===\n")

    # Test 1: Check if signin page loads
    print("1. Testing signin page...")
    response = session.get(f"{base_url}/signin/")
    if response.status_code == 200:
        print("✓ Signin page loads successfully")
    else:
        print(f"✗ Signin page failed with status {response.status_code}")
        return

    # Test 2: Login with test user
    print("\n2. Testing login...")
    # First get the signin page to extract CSRF token
    signin_response = session.get(f"{base_url}/signin/")
    csrf_token = session.cookies.get("csrftoken")

    login_data = {
        "username": "testuser",
        "password": "testpass123",
        "csrfmiddlewaretoken": csrf_token,
    }
    response = session.post(f"{base_url}/signin/", data=login_data)
    if response.status_code in [302, 200]:  # Redirect or successful login
        print("✓ Login successful")
    else:
        print(f"✗ Login failed with status {response.status_code}")
        return

    # Test 3: Access pantry page
    print("\n3. Testing pantry page access...")
    response = session.get(f"{base_url}/pantry/")
    if response.status_code == 200:
        print("✓ Pantry page loads successfully")
    else:
        print(f"✗ Pantry page failed with status {response.status_code}")
        return

    # Test 4: Add ingredient via API
    print("\n4. Testing add ingredient...")
    add_data = {"ingredient_name": "chicken"}
    response = session.post(
        f"{base_url}/pantry/add/",
        json=add_data,
        headers={"X-CSRFToken": session.cookies.get("csrftoken")},
    )
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print("✓ Ingredient added successfully")
            ingredient_id = result["ingredient"]["id"]
        else:
            print(f"✗ Failed to add ingredient: {result.get('error')}")
            return
    else:
        print(f"✗ Add ingredient failed with status {response.status_code}")
        return

    # Test 5: Get pantry ingredients
    print("\n5. Testing get pantry ingredients...")
    response = session.get(f"{base_url}/pantry/api/")
    if response.status_code == 200:
        result = response.json()
        ingredients = result.get("ingredients", [])
        if len(ingredients) > 0:
            print(f"✓ Found {len(ingredients)} ingredient(s) in pantry")
        else:
            print("✗ No ingredients found in pantry")
    else:
        print(f"✗ Get pantry failed with status {response.status_code}")

    # Test 6: Search recipes
    print("\n6. Testing recipe search...")
    response = session.get(f"{base_url}/pantry/search-recipes/")
    if response.status_code == 200:
        result = response.json()
        recipes = result.get("recipes", [])
        if len(recipes) > 0:
            print(f"✓ Found {len(recipes)} recipe suggestions")
            print(
                f"   Best match: {recipes[0]['title']} ({recipes[0]['used_ingredient_count']} ingredients matched)"
            )
        else:
            print("✓ Recipe search completed (no recipes found)")
    else:
        print(f"✗ Recipe search failed with status {response.status_code}")

    # Test 7: Delete ingredient
    print("\n7. Testing delete ingredient...")
    response = session.post(
        f"{base_url}/pantry/delete/{ingredient_id}/",
        headers={"X-CSRFToken": session.cookies.get("csrftoken")},
    )
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print("✓ Ingredient deleted successfully")
        else:
            print(f"✗ Failed to delete ingredient: {result.get('error')}")
    else:
        print(f"✗ Delete ingredient failed with status {response.status_code}")

    print("\n=== All tests completed! ===")
    print("\nTo test manually:")
    print("1. Go to http://127.0.0.1:8000/signin/")
    print("2. Login with username: testuser, password: testpass123")
    print("3. Click 'My Pantry' in the navigation")
    print("4. Add ingredients and see recipe suggestions!")


if __name__ == "__main__":
    test_pantry()
