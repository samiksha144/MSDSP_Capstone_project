USE [SOPDB]
GO

/****** Object:  StoredProcedure [dbo].[sp_register_admin]    Script Date: 23-08-2025 12:05:50 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

-- Run this in your SOPDB (or your target DB)
CREATE   PROCEDURE [dbo].[sp_register_admin]
    @username        nvarchar(50),
    @email           nvarchar(255),
    @password        nvarchar(4000),   -- plain text; will be hashed here
    @org             nvarchar(100),
    @weekly_reports  bit
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        BEGIN TRAN;

        -- prevent duplicates across admins
        IF EXISTS (
            SELECT 1 FROM dbo.admins
            WHERE LOWER(username) = LOWER(@username)
               OR LOWER(email)    = LOWER(@email)
        )
        BEGIN
            THROW 50001, 'Username or email already exists (admins).', 1;
        END

        -- hash + salt (expects dbo.ufn_hash_password to exist and return VARBINARY(32))
        DECLARE @salt VARBINARY(16) = CRYPT_GEN_RANDOM(16);
        DECLARE @hash VARBINARY(32) = dbo.ufn_hash_password(@password, @salt);

        INSERT INTO dbo.admins
            (username, email, org, weekly_reports,
             password_hash, password_salt,
             is_active, last_login, created_at, updated_at)
        VALUES
            (LOWER(@username), LOWER(@email), NULLIF(@org, ''),
             @weekly_reports,
             @hash, @salt,
             1, NULL, SYSUTCDATETIME(), SYSUTCDATETIME());

        COMMIT TRAN;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRAN;
        THROW;
    END CATCH
END
GO


