# scraper/normalize.py
import phonenumbers

def normalize_phone(raw: str) -> str:
    if not raw: return ""
    try:
        n = phonenumbers.parse(raw, "US")
        if phonenumbers.is_valid_number(n):
            return phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.NATIONAL)
    except Exception:
        pass
    return raw 
