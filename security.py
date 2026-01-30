# from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MAX_LEN = 72  # bcrypt limit

# def hash_password(password: str) -> str:
#     password = password.strip()[:MAX_LEN]
#     return pwd_context.hash(password)

# def verify_password(password: str, hashed: str) -> bool:
#     password = password.strip()[:MAX_LEN]
#     return pwd_context.verify(password, hashed)

from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


# from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MAX_LEN = 72  # bcrypt byte limit

# def _normalize_password(password: str) -> bytes:
#     return password.strip().encode("utf-8")[:MAX_LEN]

# def hash_password(password: str) -> str:
#     return pwd_context.hash(_normalize_password(password))

# def verify_password(password: str, hashed: str) -> bool:
#     return pwd_context.verify(_normalize_password(password), hashed)

