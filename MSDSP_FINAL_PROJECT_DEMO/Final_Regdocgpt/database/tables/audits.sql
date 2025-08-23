USE [SOPDB]
GO

/****** Object:  Table [dbo].[audits]    Script Date: 23-08-2025 12:03:23 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[audits](
	[id] [bigint] IDENTITY(1,1) NOT NULL,
	[ts] [datetime2](0) NOT NULL,
	[actor] [nvarchar](128) NOT NULL,
	[event] [nvarchar](256) NOT NULL,
	[detail] [nvarchar](max) NULL,
	[actor_role] [nvarchar](16) NULL,
	[admin_id] [int] NULL,
	[user_id] [int] NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[audits] ADD  CONSTRAINT [DF_audits_ts]  DEFAULT (sysutcdatetime()) FOR [ts]
GO


