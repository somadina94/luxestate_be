import time
from typing import Optional
from fastapi import Request
from jose import jwt, JWTError
from app.services.audit_log_service import AuditLogService
from app.database import SessionLocal
from app.services.auth_service import ALGORITHM, SECRET_KEY


async def audit_log_middleware(request: Request, call_next):
    """FastAPI middleware to automatically log requests and responses."""
    start_time = time.time()

    # Extract user info from Authorization header if present
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    auth_header = request.headers.get("authorization", "")
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
    ip_address = request.headers.get("x-forwarded-for") or (
        request.client.host if request.client else None
    )
    user_agent = request.headers.get("user-agent")

    db = SessionLocal()
    try:
        try:
            response = await call_next(request)
            status_code = getattr(response, "status_code", None)
            status = "success" if status_code and status_code < 400 else "failure"
            return response
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            AuditLogService().create_log(
                db=db,
                action="http.request",
                resource_type="http",
                resource_id=None,
                user_id=user_id,
                after_state=None,
                before_state=None,
                changes=None,
                status="error",
                status_code=None,
                error_message=str(exc)[:1000],
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=method,
                request_path=path,
                duration_ms=duration_ms,
            )
            raise
        finally:
            # Only log successful/failed responses here (errors handled above)
            end_duration_ms = int((time.time() - start_time) * 1000)
            # Avoid double logging when exception occurred
            if "response" in locals():
                AuditLogService().create_log(
                    db=db,
                    action="http.request",
                    resource_type="http",
                    resource_id=None,
                    user_id=user_id,
                    after_state=None,
                    before_state=None,
                    changes=None,
                    status="success" if response.status_code < 400 else "failure",
                    status_code=response.status_code,
                    error_message=None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_method=method,
                    request_path=path,
                    duration_ms=end_duration_ms,
                )
    finally:
        db.close()
