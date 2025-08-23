USE [SOPDB]
GO

/****** Object:  StoredProcedure [dbo].[sp_register_user]    Script Date: 23-08-2025 12:06:06 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

/* ===== User Registration ===== */
CREATE   PROCEDURE [dbo].[sp_register_user]
  @username NVARCHAR(50),
  @email    NVARCHAR(255),
  @password NVARCHAR(4000)
AS
BEGIN
  SET NOCOUNT ON;

  IF EXISTS (SELECT 1 FROM dbo.users WHERE username = @username) RETURN -1;
  IF EXISTS (SELECT 1 FROM dbo.users WHERE email    = @email)    RETURN -2;

  DECLARE @salt VARBINARY(16) = CRYPT_GEN_RANDOM(16);
  DECLARE @hash VARBINARY(32) = dbo.ufn_hash_password(@password, @salt);

  INSERT INTO dbo.users(username, email, password_hash, password_salt)
  VALUES (@username, @email, @hash, @salt);

  RETURN 0;
END
GO


