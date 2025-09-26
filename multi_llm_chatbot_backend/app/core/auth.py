import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from bson import ObjectId
from app.core.database import get_database
from app.models.user import User, UserResponse, PasswordReset, EmailVerification

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

# Security scheme
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email from database"""
    db = get_database()
    user_data = await db.users.find_one({"email": email})
    if user_data:
        return User(**user_data)
    return None

async def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by ID from database"""
    try:
        db = get_database()
        user_data = await db.users.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User(**user_data)
        return None
    except Exception:
        return None

async def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password"""
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user (must be verified and active)"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # For now, we'll allow unverified users to use the system
    # but you can uncomment this to require email verification
    # if not current_user.email_verified:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, 
    #         detail="Email not verified"
    #     )
    
    return current_user

def create_user_response(user: User) -> UserResponse:
    """Create a UserResponse from User model"""
    return UserResponse(
        id=str(user.id),
        firstName=user.firstName,
        lastName=user.lastName,
        email=user.email,
        academicStage=user.academicStage,
        researchArea=user.researchArea,
        created_at=user.created_at,
        last_login=user.last_login,
        email_verified=user.email_verified
    )

# Email Verification Functions

async def create_email_verification_token(email: str, user_id: str) -> Optional[EmailVerification]:
    """Create an email verification token for the user"""
    user = await get_user_by_id(user_id)
    if not user:
        return None
    
    # Delete any existing verification tokens for this user
    db = get_database()
    await db.email_verifications.delete_many({"email": email})
    
    # Create new verification token
    verification_token = EmailVerification.create_verification_token(email, user_id)
    
    # Save to database
    result = await db.email_verifications.insert_one(verification_token.dict(by_alias=True))
    verification_token.id = result.inserted_id
    
    return verification_token

async def verify_email_code(email: str, verification_code: str) -> bool:
    """Verify email code and mark user as verified"""
    db = get_database()
    
    # Find the verification token
    verification_data = await db.email_verifications.find_one({
        "email": email,
        "verification_code": verification_code,
        "used": False,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if not verification_data:
        return False
    
    # Mark verification token as used
    await db.email_verifications.update_one(
        {"_id": verification_data["_id"]},
        {"$set": {"used": True}}
    )
    
    # Mark user as email verified
    result = await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "email_verified": True,
                "email_verified_at": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0

async def resend_verification_email(email: str) -> Optional[EmailVerification]:
    """Resend verification email - creates new token"""
    user = await get_user_by_email(email)
    if not user:
        return None
    
    if user.email_verified:
        return None  # Already verified
    
    # Create new verification token
    return await create_email_verification_token(email, str(user.id))

# Password Reset Functions (keeping existing functionality)

async def create_password_reset_token(email: str) -> Optional[PasswordReset]:
    """Create a password reset token for the user"""
    user = await get_user_by_email(email)
    if not user:
        return None
    
    # Delete any existing reset tokens for this user
    db = get_database()
    await db.password_resets.delete_many({"email": email})
    
    # Create new reset token
    reset_token = PasswordReset.create_reset_token(email, str(user.id))
    
    # Save to database
    result = await db.password_resets.insert_one(reset_token.dict(by_alias=True))
    reset_token.id = result.inserted_id
    
    return reset_token

async def verify_reset_code(email: str, reset_code: str) -> Optional[PasswordReset]:
    """Verify reset code and return token if valid"""
    db = get_database()
    
    # Find the reset token
    reset_data = await db.password_resets.find_one({
        "email": email,
        "reset_code": reset_code,
        "used": False,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if reset_data:
        return PasswordReset(**reset_data)
    return None

async def reset_user_password(email: str, reset_code: str, new_password: str) -> bool:
    """Reset user password using reset code"""
    # Verify the reset code
    reset_token = await verify_reset_code(email, reset_code)
    if not reset_token:
        return False
    
    # Update user password
    db = get_database()
    hashed_password = get_password_hash(new_password)
    
    result = await db.users.update_one(
        {"email": email},
        {"$set": {"hashed_password": hashed_password}}
    )
    
    if result.modified_count > 0:
        # Mark reset token as used
        await db.password_resets.update_one(
            {"_id": reset_token.id},
            {"$set": {"used": True}}
        )
        return True
    
    return False