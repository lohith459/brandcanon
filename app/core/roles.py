from typing import Optional, List
from fastapi import Header, HTTPException, status
from app.models.submission import DemoRole

def get_current_role(x_demo_role: Optional[str] = Header(default="Creator")) -> str:
    """
    Extracts and validates the demo role from the X-Demo-Role header.
    Defaults to 'Creator' for zero-login immediate accessibility.
    """
    valid_roles = [r.value for r in DemoRole]
    if x_demo_role not in valid_roles:
        # Fallback to Creator if an unrecognized role is passed
        return DemoRole.CREATOR.value
    return x_demo_role

def require_role(allowed_roles: List[str]):
    """FastAPI dependency factory enforcing server-side role permissions."""
    def role_checker(current_role: str = Header(default="Creator", alias="X-Demo-Role")) -> str:
        if current_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Active role '{current_role}' is not authorized. Required: {', '.join(allowed_roles)}."
            )
        return current_role
    return role_checker
