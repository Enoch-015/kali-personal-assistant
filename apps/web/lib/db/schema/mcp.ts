import { int, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const mcp = sqliteTable("mcp", {
  id: int().primaryKey({ autoIncrement: true }),
  url: text().notNull().unique(),
  name: text().notNull(),
  description: text().notNull(),
  isActive: int().notNull().default(1),
  createdAt: int().notNull().$default(() => Date.now()),
  updatedAt: int().notNull().$default(() => Date.now()).$onUpdate(() => Date.now()),
});
