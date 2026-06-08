from fastapi import Header, HTTPException
import os

def verify_secret(x_secret_key: str = Header(...)):
    """Validate the secret key passed via the X-Secret-Key header.
    The secret is read from the EMMA_SECRET environment variable (default: lucy-secret).
    """
    secret = os.getenv("EMMA_SECRET", "lucy-secret")
    if x_secret_key != secret:
        raise HTTPException(status_code=401, detail="Invalid secret")
    # Return the provided secret value (truthy) so callers can access it for rate-limiting
    return x_secret_key
