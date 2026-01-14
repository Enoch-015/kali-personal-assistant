CREATE TABLE `ephemeral_key` (
	`id` text PRIMARY KEY NOT NULL,
	`key_hash` text NOT NULL,
	`prefix` text DEFAULT 'ek_' NOT NULL,
	`name` text,
	`scopes` text DEFAULT '[]',
	`user_id` text,
	`expires_at` integer NOT NULL,
	`last_used_at` integer,
	`usage_count` integer DEFAULT 0 NOT NULL,
	`max_usage` integer,
	`revoked_at` integer,
	`metadata` text DEFAULT '{}',
	`created_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	`updated_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `ephemeral_key_key_hash_unique` ON `ephemeral_key` (`key_hash`);