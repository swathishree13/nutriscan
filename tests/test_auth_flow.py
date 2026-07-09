import unittest

from app import app, db


class AuthFlowTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SECRET_KEY="test-secret"
        )
        self.app_context = app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_registration_login_and_profile(self):
        register_response = self.client.post(
            "/register",
            data={
                "full_name": "Ada Lovelace",
                "email": "ada@example.com",
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
                "terms": "on",
                "privacy": "on"
            },
            follow_redirects=True
        )
        self.assertEqual(register_response.status_code, 200)

        login_response = self.client.post(
            "/login",
            data={
                "email": "ada@example.com",
                "password": "StrongPass123!",
                "remember": "on"
            },
            follow_redirects=True
        )
        self.assertEqual(login_response.status_code, 200)

        profile_response = self.client.get("/profile")
        self.assertEqual(profile_response.status_code, 200)
        self.assertIn(b"Profile", profile_response.data)


if __name__ == "__main__":
    unittest.main()
