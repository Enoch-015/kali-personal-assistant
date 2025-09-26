import { int, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const plugin = sqliteTable("plugin", {
  id: int().primaryKey({ autoIncrement: true }),
  name: text().notNull(),
  slug: text().notNull().unique(),
  description: text().notNull(),
  version: text().notNull(),
  author: text().notNull(),
  createdAt: int().notNull().$default(() => Date.now()),
  updatedAt: int().notNull().$default(() => Date.now()).$onUpdate(() => Date.now()),
});
