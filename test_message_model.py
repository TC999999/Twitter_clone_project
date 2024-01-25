"""Message Model Tests"""

import os
from unittest import TestCase

from models import db, User, Message

from datetime import datetime

os.environ["DATABASE_URL"] = "postgresql:///warbler_test"

from app import app

db.drop_all()
db.create_all()


class MessageModelTestCase(TestCase):
    """Test models for messages"""

    def setUp(self):
        """Create Test Client"""
        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(
            username="testuser",
            email="test@test.com",
            password="testuser",
            image_url=None,
        )

        db.session.commit()

    def tearDown(self):
        """Deletes any leftovers in db.session"""
        db.session.rollback()

    def test_message_model(self):
        """Does basic model work"""

        m = Message(text="Test Message")
        self.testuser.messages.append(m)

        db.session.commit()

        self.assertEqual(m.user, self.testuser)
        self.assertEqual(m.text, "Test Message")
        self.assertEqual(type(m.timestamp), datetime)
