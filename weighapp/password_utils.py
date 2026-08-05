import re


def validate_password_strength(password):
    """
    Checks a password against the system's minimum complexity rules:
    at least 8 characters, one uppercase letter, one lowercase letter,
    and one special (non-alphanumeric) character.

    Returns a list of unmet requirement descriptions — empty list means
    the password satisfies every rule.
    """
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r'[A-Z]', password):
        errors.append("one uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.append("one lowercase letter")
    if not re.search(r'[^A-Za-z0-9]', password):
        errors.append("one special character")
    return errors