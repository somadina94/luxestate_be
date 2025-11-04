from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.models.audit_log import AuditLog
from datetime import datetime, timedelta, timezone


class AuditLogService:
    """Central service for creating and querying audit logs"""

    def create_log(
        self,
        db: Session,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        user_id: Optional[int] = None,
        changes: Optional[dict] = None,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        status: str = "success",
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> AuditLog:
        """Create an audit log entry"""
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            before_state=before_state,
            after_state=after_state,
            status=status,
            status_code=status_code,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            duration_ms=duration_ms,
        )

        db.add(log)
        try:
            db.commit()
            db.refresh(log)
        except Exception:
            # Rollback on any error (e.g., foreign key violations in tests)
            db.rollback()
            raise
        return log

    def get_logs(
        self,
        db: Session,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> List[AuditLog]:
        """Query audit logs with filters"""
        query = db.query(AuditLog)

        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if resource_type is not None:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id is not None:
            query = query.filter(AuditLog.resource_id == resource_id)
        if action is not None:
            query = query.filter(AuditLog.action == action)
        if start_date is not None:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date is not None:
            query = query.filter(AuditLog.timestamp <= end_date)

        return (
            query.order_by(desc(AuditLog.timestamp))
            .offset(skip)
            .limit(max(1, min(limit, 1000)))
            .all()
        )

    def get_user_activity(
        self, db: Session, user_id: int, days: int = 30
    ) -> List[AuditLog]:
        """Get recent activity for a specific user"""
        since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
        return (
            db.query(AuditLog)
            .filter(AuditLog.user_id == user_id, AuditLog.timestamp >= since)
            .order_by(desc(AuditLog.timestamp))
            .all()
        )

    def get_resource_history(
        self, db: Session, resource_type: str, resource_id: int
    ) -> List[AuditLog]:
        """Get complete change history for a resource"""
        return (
            db.query(AuditLog)
            .filter(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
            .order_by(asc(AuditLog.timestamp))
            .all()
        )
