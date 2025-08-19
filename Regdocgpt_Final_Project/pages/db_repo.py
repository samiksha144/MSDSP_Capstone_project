# db_repo.py
from typing import Optional, Tuple, Dict, Any, List
import pyodbc
from db_conn import sql_conn


class DBError(RuntimeError):
    pass


# =========================
# Bootstrap / Migration: audits schema (admin_id + user_id + actor_role)
# =========================
# NOTE: Keep GO separators; we split/execute batches via _exec_batch().
_AUDIT_TABLE_MIGRATE_SQL = r"""
IF NOT EXISTS (
    SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'[dbo].[audits]') AND type = N'U'
)
BEGIN
    CREATE TABLE [dbo].[audits] (
        [id]         BIGINT IDENTITY(1,1) PRIMARY KEY,
        [ts]         DATETIME2(0) NOT NULL CONSTRAINT DF_audits_ts DEFAULT (SYSUTCDATETIME()),
        [actor]      NVARCHAR(128) NOT NULL,      -- 'User' | 'Admin' | 'System' | 'Assistant'
        [actor_role] NVARCHAR(16)  NULL,          -- 'user' | 'admin' | 'system' | 'assistant'
        [admin_id]   INT           NULL,
        [user_id]    INT           NULL,
        [event]      NVARCHAR(256) NOT NULL,
        [detail]     NVARCHAR(MAX) NULL
    );
END
ELSE
BEGIN
    -- Add missing columns (idempotent)
    IF COL_LENGTH('dbo.audits', 'actor_role') IS NULL
        ALTER TABLE dbo.audits ADD actor_role NVARCHAR(16) NULL;

    IF COL_LENGTH('dbo.audits', 'admin_id') IS NULL
        ALTER TABLE dbo.audits ADD admin_id INT NULL;

    -- Convert user_id to INT if it exists but is not INT (system_type_id 56 = INT)
    DECLARE @needs_convert BIT =
    CASE WHEN EXISTS (
        SELECT 1
        FROM sys.columns
        WHERE object_id = OBJECT_ID('dbo.audits')
          AND name = 'user_id'
          AND system_type_id <> 56
    ) THEN 1 ELSE 0 END;

    IF (@needs_convert = 1)
    BEGIN
        -- 1) Add temp INT column if needed
        EXEC sp_executesql N'
            IF COL_LENGTH(''dbo.audits'',''user_id_tmp'') IS NULL
                ALTER TABLE dbo.audits ADD user_id_tmp INT NULL;
        ';

        -- 2) Copy/convert
        EXEC sp_executesql N'UPDATE dbo.audits SET user_id_tmp = TRY_CONVERT(INT, user_id);';

        -- 3) Drop known index on old user_id if present
        IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_audits_user' AND object_id = OBJECT_ID('dbo.audits'))
            DROP INDEX IX_audits_user ON dbo.audits;

        -- 4) Drop old column and rename temp -> user_id
        EXEC sp_executesql N'ALTER TABLE dbo.audits DROP COLUMN user_id;';
        EXEC sp_executesql N'EXEC sp_rename ''dbo.audits.user_id_tmp'', ''user_id'', ''COLUMN'';';
    END

    -- Remove legacy columns if they still exist
    IF COL_LENGTH('dbo.audits', 'ip') IS NOT NULL
        ALTER TABLE dbo.audits DROP COLUMN ip;
    IF COL_LENGTH('dbo.audits', 'extra') IS NOT NULL
        ALTER TABLE dbo.audits DROP COLUMN extra;
END;
GO

-- Helpful indexes (create only if missing)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_audits_ts' AND object_id = OBJECT_ID('dbo.audits'))
    CREATE INDEX IX_audits_ts ON dbo.audits (ts DESC);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_audits_actor' AND object_id = OBJECT_ID('dbo.audits'))
    CREATE INDEX IX_audits_actor ON dbo.audits (actor);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_audits_user' AND object_id = OBJECT_ID('dbo.audits'))
    CREATE INDEX IX_audits_user ON dbo.audits (user_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_audits_admin' AND object_id = OBJECT_ID('dbo.audits'))
    CREATE INDEX IX_audits_admin ON dbo.audits (admin_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_audits_event' AND object_id = OBJECT_ID('dbo.audits'))
    CREATE INDEX IX_audits_event ON dbo.audits (event);
GO
"""

# Insert proc (accepts both ids + actor_role)
_SP_ADD_AUDIT = r"""
IF OBJECT_ID(N'[dbo].[sp_add_audit]', N'P') IS NOT NULL
    DROP PROCEDURE [dbo].[sp_add_audit];
GO
CREATE PROCEDURE [dbo].[sp_add_audit]
    @actor      NVARCHAR(128),
    @actor_role NVARCHAR(16)  = NULL,   -- 'user' | 'admin' | 'system' | 'assistant'
    @admin_id   INT           = NULL,
    @user_id    INT           = NULL,
    @event      NVARCHAR(256),
    @detail     NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        INSERT INTO [dbo].[audits] ([actor],[actor_role],[admin_id],[user_id],[event],[detail])
        VALUES (@actor,@actor_role,@admin_id,@user_id,@event,@detail);
    END TRY
    BEGIN CATCH
        DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR('sp_add_audit failed: %s', 16, 1, @msg);
    END CATCH
END
GO
"""

# Read proc with filters for both ids + role
_SP_GET_AUDITS = r"""
IF OBJECT_ID(N'[dbo].[sp_get_audits]', N'P') IS NOT NULL
    DROP PROCEDURE [dbo].[sp_get_audits];
GO
CREATE PROCEDURE [dbo].[sp_get_audits]
    @actor      NVARCHAR(128) = NULL,
    @actor_role NVARCHAR(16)  = NULL,
    @admin_id   INT           = NULL,
    @user_id    INT           = NULL,
    @event      NVARCHAR(256) = NULL,
    @search     NVARCHAR(4000) = NULL, -- applies to actor/event/detail
    @limit      INT = 500,
    @offset     INT = 0
AS
BEGIN
    SET NOCOUNT ON;

    ;WITH src AS (
        SELECT id, ts, actor, actor_role, admin_id, user_id, event, detail
        FROM dbo.audits
        WHERE (@actor      IS NULL OR actor      = @actor)
          AND (@actor_role IS NULL OR actor_role = @actor_role)
          AND (@admin_id   IS NULL OR admin_id   = @admin_id)
          AND (@user_id    IS NULL OR user_id    = @user_id)
          AND (@event      IS NULL OR event      = @event)
          AND (
               @search IS NULL
            OR actor  LIKE '%' + @search + '%'
            OR event  LIKE '%' + @search + '%'
            OR detail LIKE '%' + @search + '%'
          )
    )
    SELECT id, ts, actor, actor_role, admin_id, user_id, event, detail
    FROM src
    ORDER BY ts DESC, id DESC
    OFFSET CASE WHEN @offset < 0 THEN 0 ELSE @offset END ROWS
    FETCH NEXT CASE WHEN @limit  < 1 THEN 50 ELSE @limit END ROWS ONLY;
END
GO
"""


def _exec_batch(cur, sql: str) -> None:
    """
    Execute a batch script that may contain 'GO' separators.
    Splits on lines that contain only GO (case-insensitive).
    """
    parts: List[str] = []
    acc: List[str] = []
    for line in sql.splitlines():
        if line.strip().upper() == "GO":
            parts.append("\n".join(acc).strip())
            acc = []
        else:
            acc.append(line)
    if acc:
        parts.append("\n".join(acc).strip())
    for part in parts:
        if part:
            cur.execute(part)


def ensure_audit_schema() -> None:
    """
    Create/upgrade dbo.audits table and procs (idempotent).
    Call this once on app startup.
    """
    try:
        with sql_conn() as c, c.cursor() as cur:
            _exec_batch(cur, _AUDIT_TABLE_MIGRATE_SQL)
            _exec_batch(cur, _SP_ADD_AUDIT)
            _exec_batch(cur, _SP_GET_AUDITS)
            c.commit()
    except pyodbc.Error as e:
        raise DBError(f"ensure_audit_schema failed: {e}")


# =========================
# Audits API (stored procs)
# =========================
def add_audit(
    actor: str,
    actor_role: Optional[str] = None,   # 'user' | 'admin' | 'system' | 'assistant'
    admin_id: Optional[int] = None,
    user_id: Optional[int] = None,
    event: str = "",
    detail: Optional[str] = None,
) -> None:
    """
    Generic audit insert.
    EXEC dbo.sp_add_audit @actor, @actor_role, @admin_id, @user_id, @event, @detail
    """
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute(
                """
                EXEC dbo.sp_add_audit
                    @actor=?,
                    @actor_role=?,
                    @admin_id=?,
                    @user_id=?,
                    @event=?,
                    @detail=?
                """,
                (actor, actor_role, admin_id, user_id, event, detail),
            )
            c.commit()
    except pyodbc.Error as e:
        raise DBError(f"add_audit failed: {e}")


def add_user_audit(actor: str, user_id: int, event: str, detail: Optional[str] = None) -> None:
    """Convenience wrapper for user actions."""
    add_audit(actor=actor, actor_role="user", admin_id=None, user_id=int(user_id), event=event, detail=detail)


def add_admin_audit(actor: str, admin_id: int, event: str, detail: Optional[str] = None) -> None:
    """Convenience wrapper for admin actions."""
    add_audit(actor=actor, actor_role="admin", admin_id=int(admin_id), user_id=None, event=event, detail=detail)


def add_dual_audit(actor: str, admin_id: int, user_id: int, event: str, detail: Optional[str] = None) -> None:
    """When an admin performs an action that targets a user, log both IDs."""
    add_audit(actor=actor, actor_role="admin", admin_id=int(admin_id), user_id=int(user_id), event=event, detail=detail)


def get_audits(
    actor: Optional[str] = None,
    actor_role: Optional[str] = None,
    admin_id: Optional[int] = None,
    user_id: Optional[int] = None,
    event: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Fetch audit rows via stored procedure (supports filters + pagination).
    Returns dicts with: id, ts, actor, actor_role, admin_id, user_id, event, detail
    """
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute(
                """
                EXEC dbo.sp_get_audits
                    @actor=?,
                    @actor_role=?,
                    @admin_id=?,
                    @user_id=?,
                    @event=?,
                    @search=?,
                    @limit=?,
                    @offset=?
                """,
                (actor, actor_role, admin_id, user_id, event, search, int(limit), int(offset)),
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
    except pyodbc.Error as e:
        raise DBError(f"get_audits failed: {e}")


# =========================
# Existing code (lookups, registration, profile, etc.)
# =========================
def username_taken(username: str) -> bool:
    if not username:
        return False
    q = """
    SELECT 1
    FROM (
        SELECT LOWER(username) AS u FROM dbo.users
        UNION ALL
        SELECT LOWER(username) FROM dbo.admins
    ) x
    WHERE x.u = ?
    """
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute(q, username.strip().lower())
            return cur.fetchone() is not None
    except pyodbc.Error as e:
        raise DBError(f"username_taken failed: {e}")


def email_taken(email: str) -> bool:
    if not email:
        return False
    q = """
    SELECT 1
    FROM (
        SELECT LOWER(email) AS e FROM dbo.users
        UNION ALL
        SELECT LOWER(email) FROM dbo.admins
    ) x
    WHERE x.e = ?
    """
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute(q, email.strip().lower())
            return cur.fetchone() is not None
    except pyodbc.Error as e:
        raise DBError(f"email_taken failed: {e}")


def register_user(username: str, email: str, password_plain: str) -> None:
    """Calls: EXEC dbo.sp_register_user @username, @email, @password"""
    uname = username.strip().lower()
    mail = email.strip().lower()
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute(
                """
                EXEC dbo.sp_register_user
                    @username=?,
                    @email=?,
                    @password=?
                """,
                (uname, mail, password_plain),
            )
            c.commit()

            # verify insert
            cur.execute(
                "SELECT COUNT(1) FROM dbo.users WHERE LOWER(username)=? AND LOWER(email)=?",
                (uname, mail),
            )
            if cur.fetchone()[0] == 0:
                raise DBError("sp_register_user completed but no row found in dbo.users.")
    except pyodbc.Error as e:
        raise DBError(f"register_user failed: {e}")


def register_admin(username: str, email: str, password_plain: str, org: str, weekly_reports: bool = True) -> None:
    """Calls: EXEC dbo.sp_register_admin @username, @email, @password, @org, @weekly_reports"""
    uname = username.strip().lower()
    mail = email.strip().lower()
    org_clean = (org or "").strip()
    weekly = int(bool(weekly_reports))  # BIT
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute(
                """
                EXEC dbo.sp_register_admin
                    @username=?,
                    @email=?,
                    @password=?,
                    @org=?,
                    @weekly_reports=?
                """,
                (uname, mail, password_plain, org_clean, weekly),
            )
            c.commit()

            # verify insert
            cur.execute(
                "SELECT COUNT(1) FROM dbo.admins WHERE LOWER(username)=? AND LOWER(email)=?",
                (uname, mail),
            )
            if cur.fetchone()[0] == 0:
                raise DBError("sp_register_admin completed but no row found in dbo.admins.")
    except pyodbc.Error as e:
        raise DBError(f"register_admin failed: {e}")


def get_full_profile(user_id: int) -> Dict[str, Any]:
    """
    Returns a normalized profile dict for either users/admins.
    Matches your PKs: users.user_id, admins.admin_id
    """
    q = """
    SELECT user_id AS id, 'user' AS role,
           username, email,
           COALESCE(org, '')         AS org,
           COALESCE(title, '')       AS title,
           COALESCE(phone, '')       AS phone,
           COALESCE(location, '')    AS location,
           CAST(COALESCE(weekly_reports, 0) AS INT) AS weekly_reports,
           COALESCE(created_at, GETDATE()) AS created_at,
           COALESCE(last_login, GETDATE()) AS last_login
      FROM dbo.users
     WHERE user_id = ?
    UNION ALL
    SELECT admin_id AS id, 'admin' AS role,
           username, email,
           COALESCE(org, '')         AS org,
           COALESCE(title, '')       AS title,
           COALESCE(phone, '')       AS phone,
           COALESCE(location, '')    AS location,
           CAST(COALESCE(weekly_reports, 1) AS INT) AS weekly_reports,
           COALESCE(created_at, GETDATE()) AS created_at,
           COALESCE(last_login, GETDATE()) AS last_login
      FROM dbo.admins
     WHERE admin_id = ?
    """
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute(q, (int(user_id), int(user_id)))
            row = cur.fetchone()
            if not row:
                raise DBError("Profile not found.")
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
    except pyodbc.Error as e:
        raise DBError(f"get_full_profile failed: {e}")


def update_user_profile(
    user_id: int,
    username: Optional[str] = None,
    email: Optional[str] = None,
    org: Optional[str] = None,
    title: Optional[str] = None,
    phone: Optional[str] = None,
    location: Optional[str] = None,
    weekly_reports: Optional[bool] = None,
) -> None:
    """
    Calls: EXEC dbo.sp_update_user_profile
           @user_id, @username, @email, @org, @title, @phone, @location, @weekly_reports
    """
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute(
                """
                EXEC dbo.sp_update_user_profile
                    @user_id=?,
                    @username=?,
                    @email=?,
                    @org=?,
                    @title=?,
                    @phone=?,
                    @location=?,
                    @weekly_reports=?
                """,
                (
                    int(user_id),
                    None if username is None else username.strip(),
                    None if email is None else email.strip().lower(),
                    None if org is None else org.strip(),
                    None if title is None else title.strip(),
                    None if phone is None else phone.strip(),
                    None if location is None else location.strip(),
                    None if weekly_reports is None else int(bool(weekly_reports)),
                ),
            )
            c.commit()
    except pyodbc.Error as e:
        raise DBError(f"update_user_profile failed: {e}")


def change_user_password(user_id: int, current_password: str, new_password: str) -> None:
    """Calls: EXEC dbo.sp_change_user_password @user_id, @current_password, @new_password"""
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute(
                """
                EXEC dbo.sp_change_user_password
                    @user_id=?,
                    @current_password=?,
                    @new_password=?
                """,
                (int(user_id), current_password, new_password),
            )
            c.commit()
    except pyodbc.Error as e:
        raise DBError(f"change_user_password failed: {e}")


def get_user_by_identifier(identifier: str) -> Optional[Tuple[str, str, str, str]]:
    ident = (identifier or "").strip().lower()
    if not ident:
        return None

    q = """
    SELECT 'user' AS role, username, email, COALESCE(org, '')
      FROM dbo.users
     WHERE LOWER(username) = ? OR LOWER(email) = ?
    UNION ALL
    SELECT 'admin' AS role, username, email, COALESCE(org, '')
      FROM dbo.admins
     WHERE LOWER(username) = ? OR LOWER(email) = ?
    """
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute(q, ident, ident, ident, ident)
            row = cur.fetchone()
            return tuple(row) if row else None
    except pyodbc.Error as e:
        raise DBError(f"get_user_by_identifier failed: {e}")



# -------- Optional: login lookup --------
def get_user_by_identifier(identifier: str) -> Optional[Tuple[str, str, str, str]]:
    ident = (identifier or "").strip().lower()
    if not ident:
        return None

    q = """
    SELECT 'user' AS role, username, email, COALESCE(org, '')
      FROM dbo.users
     WHERE LOWER(username) = ? OR LOWER(email) = ?
    UNION ALL
    SELECT 'admin' AS role, username, email, COALESCE(org, '')
      FROM dbo.admins
     WHERE LOWER(username) = ? OR LOWER(email) = ?
    """
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute(q, ident, ident, ident, ident)
            row = cur.fetchone()
            return tuple(row) if row else None
    except pyodbc.Error as e:
        raise DBError(f"get_user_by_identifier failed: {e}")


