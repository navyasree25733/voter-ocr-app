from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_LEN = 72  # bcrypt limit

def hash_password(password: str) -> str:
    password = password.strip()[:MAX_LEN]
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    password = password.strip()[:MAX_LEN]
    return pwd_context.verify(password, hashed)
