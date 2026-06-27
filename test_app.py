import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("app", Path(__file__).with_name("app.py"))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_chat_reply_contains_contact_info():
    reply = app.build_chat_reply("How can I contact Eman?")
    assert "emanfatima60860@gmail.com" in reply


def test_contact_message_falls_back_to_local_log(tmp_path):
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "subject": "Hello",
        "message": "Testing the contact endpoint"
    }
    sent, message = app.send_contact_email(payload, log_path=tmp_path / "messages.jsonl")
    assert sent is False
    assert (tmp_path / "messages.jsonl").exists()
    assert "saved locally" in message.lower()


def test_contact_mailto_fallback_contains_recipient_and_subject():
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "subject": "Hello",
        "message": "Testing the fallback"
    }
    mailto = app.build_contact_mailto(payload)
    assert mailto.startswith("mailto:")
    assert "emanfatima60860@gmail.com" in mailto
    assert "Hello" in mailto


def test_contact_message_uses_smtp_when_configured(monkeypatch, tmp_path):
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "subject": "Hello",
        "message": "Testing the SMTP path"
    }
    calls = {}

    class FakeSMTP:
        def __init__(self, host, port):
            calls["host"] = host
            calls["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self, context=None):
            calls["starttls"] = True

        def login(self, user, password):
            calls["login"] = (user, password)

        def send_message(self, msg):
            calls["message"] = msg

    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "sender@example.com")
    monkeypatch.setenv("SMTP_PASS", "secret")
    monkeypatch.setenv("CONTACT_TO", "emanfatima60860@gmail.com")
    monkeypatch.setattr(app.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(app.ssl, "create_default_context", lambda: object())

    sent, message = app.send_contact_email(payload, log_path=tmp_path / "messages.jsonl")

    assert sent is True
    assert "sent successfully" in message.lower()
    assert calls["message"]["To"] == "emanfatima60860@gmail.com"
    assert calls["login"] == ("sender@example.com", "secret")
