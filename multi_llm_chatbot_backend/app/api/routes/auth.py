from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime, timedelta
from bson import ObjectId
from app.models.user import UserCreate, UserLogin, User, Token, UserResponse
from app.core.auth import (
    get_password_hash, 
    authenticate_user, 
    create_access_token, 
    get_user_by_email,
    get_current_active_user,
    create_user_response,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.models.user import PasswordResetRequest, PasswordResetVerify
from app.core.auth import create_password_reset_token, reset_user_password
from app.core.email_service import email_service
from app.core.database import get_database
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/signup", response_model=Token)
async def signup(user_data: UserCreate):
    """Create a new user account"""
    try:
        db = get_database()
        
        # Check if user already exists
        existing_user = await get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            firstName=user_data.firstName,
            lastName=user_data.lastName,
            email=user_data.email,
            hashed_password=hashed_password,
            academicStage=user_data.academicStage,
            researchArea=user_data.researchArea,
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        # Insert user into database
        result = await db.users.insert_one(user.dict(by_alias=True))
        user.id = result.inserted_id
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, 
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=create_user_response(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user account"
        )

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Login with email and password"""
    try:
        # Authenticate user
        user = await authenticate_user(user_credentials.email, user_credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update last login time
        db = get_database()
        await db.users.update_one(
            {"_id": user.id},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        user.last_login = datetime.utcnow()
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, 
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=create_user_response(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return create_user_response(current_user)

@router.post("/logout")
async def logout():
    """Logout (client should discard token)"""
    return {"message": "Successfully logged out"}

@router.post("/verify-token", response_model=UserResponse)
async def verify_token(current_user: User = Depends(get_current_active_user)):
    """Verify token and return user info"""
    return create_user_response(current_user)

@router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest):
    """Request password reset - sends email with verification code"""
    try:
        # Create reset token
        reset_token = await create_password_reset_token(request.email)
        
        if not reset_token:
            # Don't reveal if email exists or not for security
            return {
                "message": "If an account with this email exists, you will receive a password reset code.",
                "success": True
            }
        
        # Send email with reset code
        email_sent = await email_service.send_password_reset_email(
            request.email, 
            reset_token.reset_code
        )
        
        if not email_sent:
            logger.error(f"Failed to send reset email to {request.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send reset email. Please try again later."
            )
        
        return {
            "message": "If an account with this email exists, you will receive a password reset code.",
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in forgot password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred. Please try again later."
        )

@router.post("/verify-reset-code")
async def verify_reset_code_endpoint(request: PasswordResetVerify):
    """Verify reset code and reset password"""
    try:
        # Validate password strength
        if len(request.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Reset password
        success = await reset_user_password(
            request.email, 
            request.reset_code, 
            request.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset code"
            )
        
        return {
            "message": "Password reset successfully",
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in verify reset code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred. Please try again later."
        )