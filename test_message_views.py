"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Likes

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

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config["WTF_CSRF_ENABLED"] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Likes.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(
            username="testuser",
            email="test@test.com",
            password="testuser",
            image_url=None,
        )

        self.testuser2 = User.signup(
            username="testuser2",
            email="test2@test.com",
            password="testuser2",
            image_url=None,
        )

        db.session.commit()

    def tearDown(self):
        """Deletes any leftovers in db.session"""
        db.session.rollback()

    def test_add_message(self):
        """Can user add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:
        test_id = self.testuser.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_add_message_other_user(self):
        """Can a user not add a message for another user?"""

        test_id = self.testuser.id
        test_id_2 = self.testuser2.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.post("/messages/new", data={"text": "Hello"})
            msg = Message.query.filter_by(user_id=test_id).all()
            self.assertTrue(msg)
            msg2 = Message.query.filter_by(user_id=test_id_2).all()
            self.assertFalse(msg2)

    def test_delete_message(self):
        """Can user delete a message?"""

        test_id = self.testuser.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.post("/messages/new", data={"text": "Hello"})

            msg = Message.query.one()
            self.assertEqual(msg.user_id, test_id)

            resp2 = c.post(f"/messages/{msg.id}/delete")
            self.assertEqual(resp2.status_code, 302)
            self.assertEqual(resp2.location, f"/users/{test_id}")

            resp3 = c.get(f"/messages/{msg.id}")
            self.assertEqual(resp3.status_code, 404)

    def test_delete_other_user_message_redirect(self):
        """Will the user be redirected away from deleting another user's message"""

        test_id = self.testuser.id
        test_id_2 = self.testuser2.id

        msg = Message(text="Hello")

        self.testuser2.messages.append(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            msg = Message.query.one()
            self.assertEqual(msg.user_id, test_id_2)

            resp = c.post(f"/messages/{msg.id}/delete")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_delete_other_user_message(self):
        """Will the user be prohibited from deleting another user's message"""

        test_id = self.testuser.id

        msg = Message(text="Hello")

        self.testuser2.messages.append(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            msg = Message.query.one()

            resp = c.post(f"/messages/{msg.id}/delete", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<div class="alert alert-danger">You can only delete your own messages.</div>',
                html,
            )

    def test_add_message_logged_out(self):
        """Will the user be prohibited from adding messages when logged out"""

        with self.client as c:
            resp = c.post("/messages/new", data={"text": "Hello"})

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

            msg = Message.query.one_or_none()
            self.assertIsNone(msg)

    def test_add_message_logged_out_redirect(self):
        """Will the user be redirected to the homepage from adding messages when logged out"""

        with self.client as c:
            resp = c.post(
                "/messages/new", data={"text": "Hello"}, follow_redirects=True
            )
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<div class="alert alert-danger">Access unauthorized.</div>', html
            )

    def test_delete_message_logged_out(self):
        """Will the user be prohibited from deleting messages when logged out"""

        msg = Message(text="Hello")
        self.testuser.messages.append(msg)
        db.session.commit()

        with self.client as c:
            resp = c.post(f"/messages/{msg.id}/delete")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

            msg = Message.query.one_or_none()
            self.assertIsNotNone(msg)

    def test_delete_message_logged_out_redirect(self):
        """Will the user be redirected to the homepage from deleting messages when logged out"""

        msg = Message(text="Hello")
        self.testuser.messages.append(msg)
        db.session.commit()

        with self.client as c:
            resp = c.post(f"/messages/{msg.id}/delete", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<div class="alert alert-danger">Access unauthorized.</div>', html
            )

    def test_like_redirect_home_page(self):
        """Can the user like another post from the home page?"""

        test_id = self.testuser.id

        msg = Message(text="Test Message")
        self.testuser2.messages.append(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            liked_message = Message.query.one()

            resp = c.post(f"/users/add_like/{liked_message.id}?redirect=/")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_like_redirect_message_page(self):
        """Can the user like another post from another user's message page?"""

        test_id = self.testuser.id
        test_id_2 = self.testuser2.id

        msg = Message(text="Test Message")
        self.testuser2.messages.append(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            liked_message = Message.query.one()

            resp = c.post(
                f"/users/add_like/{liked_message.id}?redirect=/users/{test_id_2}"
            )
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"/users/{test_id_2}")

    def test_like_route(self):
        """Can the user like another post and see the like page?"""

        test_id = self.testuser.id
        msg = Message(text="Test Message")
        self.testuser2.messages.append(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            liked_message = Message.query.one()

            resp = c.post(
                f"/users/add_like/{liked_message.id}?redirect=/", follow_redirects=True
            )

            liked_message = Message.query.one()
            like = Likes.query.one()

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(liked_message.id, like.message_id)
            self.assertEqual(test_id, like.user_id)

    def test_unlike_route(self):
        """Can the user unlike another post?"""

        test_id = self.testuser.id
        msg = Message(text="Test Message")
        self.testuser2.messages.append(msg)
        self.testuser.likes.append(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            liked_message = Likes.query.one()
            msg = Message.query.one()
            self.assertEqual(msg.id, liked_message.message_id)
            self.assertEqual(test_id, liked_message.user_id)

            resp = c.post(
                f"/users/remove_like/{liked_message.message_id}?redirect=/",
                follow_redirects=True,
            )

            liked_message = Likes.query.one_or_none()

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(liked_message, None)

    def test_unlike_redirect(self):
        """Will the user be redirected when they unlike another post?"""

        test_id = self.testuser.id
        msg = Message(text="Test Message")
        self.testuser2.messages.append(msg)
        self.testuser.likes.append(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            liked_message = Likes.query.one()

            resp = c.post(f"/users/remove_like/{liked_message.message_id}?redirect=/")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_like_logged_out_redirect(self):
        """Will the user be redirected when trying to like a message when logged out"""

        msg = Message(text="Test Message")
        self.testuser2.messages.append(msg)
        db.session.commit()

        with self.client as c:
            message = Message.query.one()

            resp = c.post(f"/users/remove_like/{message.id}?redirect=/")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_like_logged_out_page(self):
        """Can the user not like a message when logged out"""

        msg = Message(text="Test Message")
        self.testuser2.messages.append(msg)
        db.session.commit()

        with self.client as c:
            liked_message = Message.query.one()

            resp = c.post(
                f"/users/remove_like/{liked_message.id}?redirect=/",
                follow_redirects=True,
            )
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<div class="alert alert-danger">Access unauthorized.</div>',
                html,
            )
