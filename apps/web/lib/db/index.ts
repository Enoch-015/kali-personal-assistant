import { neon } from "@neondatabase/serverless";
import { drizzle } from "drizzle-orm/neon-http";

import env from "../env";
import * as schema from "./schema";

const db = drizzle({
  client: neon(env.NEON_DATABASE_URL),
  schema,
});

export default db;
