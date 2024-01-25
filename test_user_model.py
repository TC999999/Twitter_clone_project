"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follows
from sqlalchemy.exc import IntegrityError

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ["DATABASE_URL"] = "postgresql:///warbler_test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD",
            image_url=None,
        )
        self.testuser2 = User.signup(
            email="test2@test.com",
            username="testuser2",
            password="HASHED_PASSWORD_2",
            image_url=None,
        )

        db.session.commit()

    def tearDown(self):
        """Deletes any leftovers in db.session"""
        db.session.rollback()

    def test_user_model(self):
        """Does basic model work?"""

        # User should have no messages & no followers
        self.assertEqual(len(self.testuser.messages), 0)
        self.assertEqual(len(self.testuser.followers), 0)
        self.assertEqual(len(self.testuser.following), 0)
        self.assertEqual(len(self.testuser.likes), 0)
        self.assertEqual(
            self.testuser.__repr__(),
            f"<User #{self.testuser.id}: testuser, test@test.com>",
        )

    def test_invalid_credentials(self):
        """Tests if signup function fails if the credentials are invalid"""
        try:
            non_unique_username = User.signup(
                email="test123@test.com",
                username="testuser",
                password="NEW_PASSWORD",
                image_url=None,
            )
        except:
            self.assertRaises(IntegrityError)

        try:
            non_unique_email = User.signup(
                email="test@test.com",
                username="testuser3",
                password="NEXT_PASSWORD",
                image_url=None,
            )
        except:
            self.assertRaises(IntegrityError)

        try:
            no_image_url = User.signup(
                email="test456@test.com",
                username="testuser4",
                password="ANOTHER_PASSWORD",
            )
        except:
            self.assertRaises(TypeError)

    def test_users_following(self):
        """Tests if a user is following another user"""

        self.assertFalse(self.testuser.is_following(self.testuser2))
        self.assertFalse(self.testuser2.is_followed_by(self.testuser))

        self.testuser.following.append(self.testuser2)
        db.session.commit()

        self.assertTrue(self.testuser.is_following(self.testuser2))
        self.assertTrue(self.testuser2.is_followed_by(self.testuser))

    def test_user_authentication(self):
        """Tests user authentication for when they login in"""

        self.assertFalse(self.testuser.authenticate("testuser", "DIFFERENT_PASSWORD"))
        self.assertFalse(self.testuser.authenticate("test_user", "HASHED_PASSWORD"))
        self.assertEqual(
            self.testuser.authenticate("testuser", "HASHED_PASSWORD"), self.testuser
        )

    def test_user_likes(self):
        """Tests if user can like a message"""
        self.assertFalse(self.testuser.likes)
        msg = Message(text="test message")
        self.testuser2.messages.append(msg)
        self.testuser.likes.append(msg)
        self.assertTrue(self.testuser.likes)
