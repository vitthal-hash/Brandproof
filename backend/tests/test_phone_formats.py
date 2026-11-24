"""Indian mobile numbers are found in the formats people actually write them in, without catching other numbers."""
from app.engine.rules import PII_PATTERNS

PHONE = PII_PATTERNS["phone"]


def test_common_phone_formats_are_found():
    for t in ("9876543210", "98765 43210", "98765-43210", "+919876543210", "+91 98765 43210", "+91-98765-43210", "call 91 98765 43210 now"):
        assert PHONE.search(t), t


def test_other_numbers_are_not_phone_numbers():
    for t in ("2345 6789 0123", "4111 1111 1111 1111", "123456789012", "Rates up to 6.5% on 5 lakh", "5 million customers", "1234567890"):
        assert not PHONE.search(t), t
