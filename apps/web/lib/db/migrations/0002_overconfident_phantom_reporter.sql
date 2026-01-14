CREATE TABLE `livekit_session` (
	`id` text PRIMARY KEY NOT NULL,
	`room_name` text NOT NULL,
	`room_sid` text,
	`user_id` text,
	`ephemeral_key_id` text,
	`status` text DEFAULT 'pending' NOT NULL,
	`participant_name` text,
	`participant_identity` text,
	`transcript_url` text,
	`recording_url` text,
	`metadata` text DEFAULT '{}',
	`started_at` integer,
	`ended_at` integer,
	`created_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	`updated_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
CREATE TABLE `mcp` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`url` text NOT NULL,
	`name` text NOT NULL,
	`description` text NOT NULL,
	`isActive` integer DEFAULT 1 NOT NULL,
	`createdAt` integer NOT NULL,
	`updatedAt` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `mcp_url_unique` ON `mcp` (`url`);--> statement-breakpoint
CREATE TABLE `user_config` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`voice_enabled` integer DEFAULT true,
	`preferred_voice` text DEFAULT 'alloy',
	`speech_rate` integer DEFAULT 100,
	`system_prompt` text,
	`instructions` text,
	`ai_model` text DEFAULT 'gpt-4',
	`temperature` integer DEFAULT 70,
	`max_tokens` integer DEFAULT 2048,
	`memory_enabled` integer DEFAULT true,
	`context_window_size` integer DEFAULT 10,
	`notifications_enabled` integer DEFAULT true,
	`email_notifications` integer DEFAULT false,
	`theme` text DEFAULT 'system',
	`language` text DEFAULT 'en',
	`custom_settings` text DEFAULT '{}',
	`created_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	`updated_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `user_config_user_id_unique` ON `user_config` (`user_id`);