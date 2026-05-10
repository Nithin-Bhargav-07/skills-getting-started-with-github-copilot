"""
Unit tests for the Mergington High School activities API.

Tests cover the main routes and error cases for viewing activities,
signing up for activities, and unregistering from activities.
"""

import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Fixture to reset the in-memory activities state between tests.
    
    This creates a snapshot of the initial state before each test,
    and restores it after the test completes to ensure test isolation.
    """
    original_state = copy.deepcopy(activities)
    yield
    # Restore the original state after the test
    activities.clear()
    activities.update(original_state)


class TestRootRoute:
    """Tests for the root path redirect."""

    def test_root_redirects_to_static(self, client):
        """GET / should redirect to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestGetActivities:
    """Tests for the GET /activities endpoint."""

    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """GET /activities should return a JSON object with all activities."""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify the response is a dict
        assert isinstance(data, dict)
        
        # Verify known activities are present
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Verify activity structure
        activity = data["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)

    def test_get_activities_no_cache_header(self, client, reset_activities):
        """GET /activities should have Cache-Control: no-store header."""
        response = client.get("/activities")
        
        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        assert "no-store" in response.headers["Cache-Control"]


class TestSignupRoute:
    """Tests for the POST /activities/{activity_name}/signup endpoint."""

    def test_signup_success(self, client, reset_activities):
        """Signing up an email to an activity should add them to participants."""
        email = "new-student@mergington.edu"
        activity_name = "Basketball Team"
        
        # Verify the student is not already signed up
        assert email not in activities[activity_name]["participants"]
        
        # Sign them up
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify the student was added to participants
        assert email in activities[activity_name]["participants"]

    def test_signup_duplicate_email_fails(self, client, reset_activities):
        """Signing up an email that is already registered should fail."""
        activity_name = "Chess Club"
        # michael@mergington.edu is already signed up for Chess Club
        email = "michael@mergington.edu"
        
        assert email in activities[activity_name]["participants"]
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_nonexistent_activity_fails(self, client, reset_activities):
        """Signing up for a nonexistent activity should return 404."""
        email = "student@mergington.edu"
        activity_name = "Nonexistent Activity"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]


class TestUnregisterRoute:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint."""

    def test_unregister_success(self, client, reset_activities):
        """Unregistering an email should remove them from participants."""
        activity_name = "Chess Club"
        # michael@mergington.edu is already signed up for Chess Club
        email = "michael@mergington.edu"
        
        assert email in activities[activity_name]["participants"]
        
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify the student was removed from participants
        assert email not in activities[activity_name]["participants"]

    def test_unregister_not_signed_up_fails(self, client, reset_activities):
        """Unregistering an email that is not signed up should fail."""
        activity_name = "Basketball Team"
        email = "not-signed-up@mergington.edu"
        
        assert email not in activities[activity_name]["participants"]
        
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]

    def test_unregister_nonexistent_activity_fails(self, client, reset_activities):
        """Unregistering from a nonexistent activity should return 404."""
        email = "student@mergington.edu"
        activity_name = "Nonexistent Activity"
        
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]


class TestStateIsolation:
    """Tests to verify state isolation between test runs."""

    def test_state_reset_between_tests(self, client, reset_activities):
        """Verify that the reset_activities fixture properly isolates state."""
        activity_name = "Soccer Club"
        email = "test-student@mergington.edu"
        
        # Sign up
        client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert email in activities[activity_name]["participants"]
    
    def test_state_is_clean_in_new_test(self, client, reset_activities):
        """Verify that a new test starts with a clean state."""
        activity_name = "Soccer Club"
        email = "test-student@mergington.edu"
        
        # This should not be in the participants list if reset worked
        assert email not in activities[activity_name]["participants"]
