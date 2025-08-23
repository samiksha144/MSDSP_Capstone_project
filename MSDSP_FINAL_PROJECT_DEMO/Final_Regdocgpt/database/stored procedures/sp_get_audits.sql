USE [SOPDB]
GO

/****** Object:  StoredProcedure [dbo].[sp_get_audits]    Script Date: 23-08-2025 12:04:26 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
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


