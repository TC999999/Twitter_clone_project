"""User Views Test"""

import os
from unittest import TestCase

from models import db, connect_db, Message, User, Follows, Likes

os.environ["DATABASE_URL"] = "postgresql:///warbler_test"

from app import app, CURR_USER_KEY


db.drop_all()
db.create_all()

app.config["WTF_CSRF_ENABLED"] = False


class UserViewsTestCase(TestCase):
    """Test Views for User"""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()
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

    def test_logout_redirect(self):
        """will the user be reidirected when logging out"""
        test_id = self.testuser.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.get("/logout")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_logout(self):
        """Can the user logout"""
        test_id = self.testuser.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.get("/logout", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<h1>What's Happening?</h1>", html)

    def test_follow_route(self):
        """Can the user follow another user when logged in?"""
        test_id = self.testuser.id
        test_id_2 = self.testuser2.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.post(f"/users/follow/{test_id_2}")

            self.assertEqual(resp.status_code, 302)

            fllw = Follows.query.one()
            self.assertEqual(fllw.user_following_id, test_id)
            self.assertEqual(fllw.user_being_followed_id, test_id_2)

    def test_follow_route_redirect_logged_out(self):
        """user is redirected to the main page when trying to follow someone when not logged in"""
        test_id_2 = self.testuser2.id

        with self.client as c:
            resp = c.post(f"/users/follow/{test_id_2}")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_follow_route_logged_out(self):
        """user cannot follow someone when not logged in"""
        test_id_2 = self.testuser2.id

        with self.client as c:
            resp = c.post(f"/users/follow/{test_id_2}", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<div class="alert alert-danger">Access unauthorized.</div>', html
            )

    def test_own_following_page(self):
        """Can the user see their own following page when logged in?"""
        test_id = self.testuser.id

        self.testuser.following.append(self.testuser2)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.get(f"/users/{test_id}/following")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<p>@testuser2</p>", html)
            self.assertIn(
                "Edit Profile",
                html,
            )

    def test_own_following_page_logout_redirect(self):
        """will the user be redirected from seeing their own following page when logged out?"""
        test_id = self.testuser.id

        self.testuser.following.append(self.testuser2)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id}/following")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_own_following_page_logout(self):
        """Can the user be unable to see their own following page when logged out?"""
        test_id = self.testuser.id

        self.testuser.following.append(self.testuser2)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id}/following", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<div class="alert alert-danger">Access unauthorized.</div>',
                html,
            )

    def test_other_following_page(self):
        """Can the user see another user's following page when logged in?"""
        test_id = self.testuser.id
        test_id_2 = self.testuser2.id

        self.testuser2.following.append(self.testuser)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.get(f"/users/{test_id_2}/following")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<p>@testuser</p>", html)
            self.assertNotIn(
                "Edit Profile",
                html,
            )

    def test_other_following_page_logout_redirect(self):
        """will the user be redirected from seeing another user's following page when logged out?"""
        test_id_2 = self.testuser2.id

        self.testuser2.following.append(self.testuser)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id_2}/following")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_other_following_page_logout(self):
        """Can the user be unable to see another user's following page when logged out?"""
        test_id_2 = self.testuser2.id

        self.testuser2.following.append(self.testuser)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id_2}/following", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<div class="alert alert-danger">Access unauthorized.</div>',
                html,
            )

    def test_own_follower_page(self):
        """Can the user see their own followers page when logged in"""
        test_id = self.testuser.id

        self.testuser.followers.append(self.testuser2)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.get(f"/users/{test_id}/followers")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<p>@testuser2</p>", html)
            self.assertIn(
                "Edit Profile",
                html,
            )

    def test_own_follower_page_logout_redirect(self):
        """will the user be redirected from seeing their own followers page when logged out?"""
        test_id = self.testuser.id

        self.testuser.followers.append(self.testuser2)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id}/followers")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_own_following_page_logout(self):
        """Can the user be unable to see their own followers page when logged out?"""
        test_id = self.testuser.id

        self.testuser.followers.append(self.testuser2)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id}/followers", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<div class="alert alert-danger">Access unauthorized.</div>',
                html,
            )

    def test_other_follower_page(self):
        """Can the user see another user's followers page when logged in"""

        test_id = self.testuser.id
        test_id_2 = self.testuser2.id

        self.testuser2.followers.append(self.testuser)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.get(f"/users/{test_id_2}/followers")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<p>@testuser</p>", html)
            self.assertNotIn(
                "Edit Profile",
                html,
            )

    def test_other_follower_page_logout_redirect(self):
        """will the user be redirected from seeing another user's followers page when logged out?"""

        test_id_2 = self.testuser2.id

        self.testuser2.followers.append(self.testuser)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id_2}/followers")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_other_following_page_logout(self):
        """Can the user be unable to see another user's followers page when logged out?"""

        test_id_2 = self.testuser2.id

        self.testuser2.followers.append(self.testuser)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id_2}/followers", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<div class="alert alert-danger">Access unauthorized.</div>',
                html,
            )

    def test_unfollow_redirect(self):
        """Will the user be redirected when unfollowing another user"""

        test_id = self.testuser.id
        test_id_2 = self.testuser2.id

        self.testuser.following.append(self.testuser2)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.post(f"/users/stop-following/{test_id_2}")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f"/users/{test_id}/following")

    def test_unfollow_route(self):
        """Can the user unfollow another user?"""

        test_id = self.testuser.id
        test_id_2 = self.testuser2.id

        self.testuser.following.append(self.testuser2)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.post(f"/users/stop-following/{test_id_2}", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("<p>@testuser2</p>", html)

    def test_own_like_page(self):
        """Can the user see their own liked page"""

        test_id = self.testuser.id
        msg = Message(text="Test Message")
        self.testuser2.messages.append(msg)
        self.testuser.likes.append(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.get(f"/users/{test_id}/liked")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<p>Test Message</p>", html)

    def test_own_like_page_logged_out_redirect(self):
        """Will the user be redirected from their own liked page when logged out?"""

        test_id = self.testuser.id
        msg = Message(text="Test Message")
        self.testuser2.messages.append(msg)
        self.testuser.likes.append(msg)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id}/liked")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_own_like_page_logged_out(self):
        """Can the user not see their own liked page when logged out?"""

        test_id = self.testuser.id
        msg = Message(text="Test Message")
        self.testuser2.messages.append(msg)
        self.testuser.likes.append(msg)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id}/liked", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<div class="alert alert-danger">Access unauthorized.</div>',
                html,
            )

    def test_other_like_page(self):
        """Can the user see another user's liked page"""

        test_id = self.testuser2.id
        test_id_2 = self.testuser2.id
        msg = Message(text="Test Message")
        self.testuser.messages.append(msg)
        self.testuser2.likes.append(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = test_id

            resp = c.get(f"/users/{test_id_2}/liked")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<p>Test Message</p>", html)

    def test_own_like_page_logged_out_redirect(self):
        """Will the user be redirected from another user's liked page when logged out?"""

        test_id_2 = self.testuser2.id
        msg = Message(text="Test Message")
        self.testuser.messages.append(msg)
        self.testuser2.likes.append(msg)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id_2}/liked")

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

    def test_own_like_page_logged_out(self):
        """Can the user not see another user's liked page when logged out?"""

        test_id_2 = self.testuser.id
        msg = Message(text="Test Message")
        self.testuser.messages.append(msg)
        self.testuser2.likes.append(msg)
        db.session.commit()

        with self.client as c:
            resp = c.get(f"/users/{test_id_2}/liked", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<div class="alert alert-danger">Access unauthorized.</div>',
                html,
            )
