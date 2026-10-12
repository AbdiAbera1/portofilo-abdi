import os
import smtplib
import unittest
from unittest.mock import patch

import app


class ContactFormTests(unittest.TestCase):
    def setUp(self):
        app.app.config.update(TESTING=True)
        app.RATE_LIMITS.clear()
        self.client = app.app.test_client()
        self.payload = {
            "name": "Test Visitor",
            "email": "visitor@example.com",
            "request": "Website development",
            "message": "I would like to discuss a website project.",
            "website": "",
        }

    def test_contact_form_sends_email_to_owner_with_reply_to(self):
        with (
            patch.dict(os.environ, {"GMAIL_APP_PASSWORD": "test-password"}),
            patch("app.smtplib.SMTP") as smtp_class,
        ):
            smtp = smtp_class.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            response = self.client.post("/api/contact", json=self.payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["message"], "Your message has been sent.")
        smtp.login.assert_called_once_with(app.RECIPIENT, "test-password")
        sent_message = smtp.send_message.call_args.args[0]
        self.assertEqual(sent_message["To"], app.RECIPIENT)
        self.assertEqual(sent_message["Reply-To"], self.payload["email"])
        self.assertIn(self.payload["message"], sent_message.get_content())

    def test_invalid_email_is_rejected(self):
        payload = {**self.payload, "email": "not-an-email"}

        response = self.client.post("/api/contact", json=payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "Please enter a valid email address.")

    def test_honeypot_submission_is_rejected(self):
        payload = {**self.payload, "website": "spam"}

        response = self.client.post("/api/contact", json=payload)

        self.assertEqual(response.status_code, 400)

    def test_missing_email_configuration_returns_service_error(self):
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post("/api/contact", json=self.payload)

        self.assertEqual(response.status_code, 503)

    def test_smtp_failure_is_reported(self):
        with (
            patch.dict(os.environ, {"GMAIL_APP_PASSWORD": "test-password"}),
            patch("app.smtplib.SMTP") as smtp_class,
        ):
            smtp = smtp_class.return_value.__enter__.return_value
            smtp.send_message.side_effect = smtplib.SMTPException("mail server unavailable")

            response = self.client.post("/api/contact", json=self.payload)

        self.assertEqual(response.status_code, 502)
        self.assertIn("could not be sent", response.json["error"])

    def test_rate_limit_rejects_sixth_message_from_same_ip(self):
        with (
            patch.dict(os.environ, {"GMAIL_APP_PASSWORD": "test-password"}),
            patch("app.smtplib.SMTP") as smtp_class,
        ):
            smtp_class.return_value.__enter__.return_value.send_message.return_value = {}
            responses = [
                self.client.post("/api/contact", json=self.payload)
                for _ in range(app.RATE_LIMIT_MAX_REQUESTS + 1)
            ]

        self.assertTrue(all(response.status_code == 200 for response in responses[:-1]))
        self.assertEqual(responses[-1].status_code, 429)


if __name__ == "__main__":
    unittest.main()
