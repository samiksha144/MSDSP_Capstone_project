USE [SOPDB]
GO

/****** Object:  StoredProcedure [dbo].[sp_add_audit]    Script Date: 23-08-2025 12:04:04 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
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


