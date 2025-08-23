USE [SOPDB]
GO

/****** Object:  Table [dbo].[users]    Script Date: 23-08-2025 12:02:36 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[users](
	[user_id] [int] IDENTITY(1,1) NOT NULL,
	[username] [nvarchar](50) NOT NULL,
	[email] [nvarchar](255) NOT NULL,
	[password_hash] [varbinary](32) NOT NULL,
	[password_salt] [varbinary](16) NOT NULL,
	[is_active] [bit] NOT NULL,
	[last_login] [datetime2](3) NULL,
	[created_at] [datetime2](3) NOT NULL,
	[updated_at] [datetime2](3) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[user_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[email] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[username] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[users] ADD  DEFAULT ((1)) FOR [is_active]
GO

ALTER TABLE [dbo].[users] ADD  DEFAULT (sysutcdatetime()) FOR [created_at]
GO

ALTER TABLE [dbo].[users] ADD  DEFAULT (sysutcdatetime()) FOR [updated_at]
GO


