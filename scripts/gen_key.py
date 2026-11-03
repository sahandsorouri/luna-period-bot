"""Print a new MASTER_KEY. Put it in .env and back it up apart from the database."""
import base64
import secrets

print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
