USE [SOPDB]
GO

/****** Object:  StoredProcedure [dbo].[sp_login_admin]    Script Date: 23-08-2025 12:04:48 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE   PROCEDURE [dbo].[sp_login_admin]
  @username_or_email NVARCHAR(255),
  @password          NVARCHAR(4000)
AS
BEGIN
  DECLARE @admin_id INT, @hash VARBINARY(32), @salt VARBINARY(16), @is_active BIT;

  SELECT TOP(1)
      @admin_id = admin_id,
      @hash     = password_hash,
      @salt     = password_salt,
      @is_active = is_active
  FROM dbo.admins
  WHERE username = @username_or_email OR email = @username_or_email;

  IF @admin_id IS NULL   RETURN -1;
  IF @is_active = 0      RETURN -2;

  IF dbo.ufn_hash_password(@password, @salt) = @hash
  BEGIN
    UPDATE dbo.admins SET last_login = SYSUTCDATETIME() WHERE admin_id = @admin_id;
    RETURN 0;
  END
  ELSE RETURN -3;
END
GO


