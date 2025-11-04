import time
from typing import Optional
from fastapi import Request, BackgroundTasks
from jose import jwt, JWTError
from app.services.audit_log_service import AuditLogService
from app.database import SessionLocal
from app.services.auth_service import ALGORITHM, SECRET_KEY
import asyncio
from concurrent.futures import ThreadPoolExecutor


# Thread pool for executing blocking database operations
_executor = ThreadPoolExecutor(max_workers=5)


def _log_audit_sync(
    user_id: Optional[int],
    status: str,
    status_code: Optional[int],
    error_message: Optional[str],
    ip_address: Optional[str],
    user_agent: Optional[str],
    method: str,
    path: str,
    duration_ms: int,
):
    """Synchronous function to log audit entry - runs in thread pool.
    
    Gracefully handles foreign key violations and other database errors
    to ensure audit logging never breaks the main request flow.
    """
    db = SessionLocal()
    try:
        # Validate user_id exists if provided (to avoid foreign key violations)
        validated_user_id = user_id
        if user_id is not None:
            from app.models.user import User
            user_exists = db.query(User).filter(User.id == user_id).first() is not None
            if not user_exists:
                # User doesn't exist, set to None to avoid foreign key violation
                validated_user_id = None
        
        AuditLogService().create_log(
            db=db,
            action="http.request",
            resource_type="http",
            resource_id=None,
            user_id=validated_user_id,
            after_state=None,
            before_state=None,
            changes=None,
            status=status,
            status_code=status_code,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=method,
            request_path=path,
            duration_ms=duration_ms,
        )
    except Exception as e:
        # Silently ignore audit logging errors - they should never break the request
        # This commonly happens in tests when transactions rollback before audit logs commit
        # Log to console in development for debugging
        import sys
        from sqlalchemy.exc import IntegrityError
        
        # Rollback any partial transaction
        try:
            db.rollback()
        except Exception:
            pass  # Ignore rollback errors too
        
        # Only log in debug mode or if it's not a foreign key violation
        if sys.flags.debug and not isinstance(e, IntegrityError):
            print(f"Audit logging failed (non-critical): {e}", file=sys.stderr)
    finally:
        try:
            db.close()
        except Exception:
            pass  # Ignore close errors


async def audit_log_middleware(request: Request, call_next):
    """FastAPI middleware to automatically log requests and responses.
    
    Uses background tasks to avoid blocking request processing.
    Disabled in test environment to avoid foreign key violations.
    """
    # Skip audit logging in test environment
    import os
    if os.getenv("TESTING") == "true":
        return await call_next(request)
    
    start_time = time.time()

    # Extract user info from Authorization header if present
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    auth_header = request.headers.get("authorization", "")
    
    # Only decode JWT if there's an auth header (skip for most requests)
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_email = payload.get("sub")
            user_id = payload.get("id")
            user_role = payload.get("role")
        except JWTError:
            # Ignore token errors in middleware; endpoint will handle auth
            pass

    method = request.method
    path = request.url.path

    # Bypass audit logging for health checks and static assets
    if path in ["/healthy", "/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)
    
    ip_address = request.headers.get("x-forwarded-for") or (
        request.client.host if request.client else None
    )
    user_agent = request.headers.get("user-agent")

    try:
        response = await call_next(request)
        status_code = getattr(response, "status_code", None)
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log asynchronously in background - doesn't block response
        status = "success" if status_code and status_code < 400 else "failure"
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            _executor,
            _log_audit_sync,
            user_id,
            status,
            status_code,
            None,
            ip_address,
            user_agent,
            method,
            path,
            duration_ms,
        )
        return response
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        # Log errors synchronously (but still in thread pool to avoid blocking)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            _executor,
            _log_audit_sync,
            user_id,
            "error",
            None,
            str(exc)[:1000],
            ip_address,
            user_agent,
            method,
            path,
            duration_ms,
        )
        raise
