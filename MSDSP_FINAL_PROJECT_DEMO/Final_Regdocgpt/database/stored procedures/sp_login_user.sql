USE [SOPDB]
GO

/****** Object:  StoredProcedure [dbo].[sp_login_user]    Script Date: 23-08-2025 12:05:28 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE   PROCEDURE [dbo].[sp_login_user]
  @username_or_email NVARCHAR(255),
  @password          NVARCHAR(4000)
AS
BEGIN
  DECLARE @user_id INT, @hash VARBINARY(32), @salt VARBINARY(16), @is_active BIT;

  SELECT TOP(1)
      @user_id = user_id,
      @hash    = password_hash,
      @salt    = password_salt,
      @is_active = is_active
  FROM dbo.users
  WHERE username = @username_or_email OR email = @username_or_email;

  IF @user_id IS NULL   RETURN -1;
  IF @is_active = 0     RETURN -2;

  IF dbo.ufn_hash_password(@password, @salt) = @hash
  BEGIN
    UPDATE dbo.users SET last_login = SYSUTCDATETIME() WHERE user_id = @user_id;
    RETURN 0;
  END
  ELSE RETURN -3;
END
GO


