from email_validator import validate_email, EmailNotValidError
def valid_email(value):
    try: validate_email(value,check_deliverability=False); return True
    except EmailNotValidError: return False
