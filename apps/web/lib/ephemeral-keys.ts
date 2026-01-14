import { and, eq, gt, isNull, sql } from "drizzle-orm";
import crypto from "uncrypto";

import type { EphemeralKey, NewEphemeralKey } from "./db/schema";

import db from "./db";
import { ephemeralKey } from "./db/schema";

// ============================================================
// Types
// ============================================================

export type GenerateKeyOptions = {
  /** Human-readable name for the key */
  name?: string;
  /** Scopes/permissions for the key */
  scopes?: string[];
  /** Associated user ID (optional) */
  userId?: string;
  /** Time-to-live in seconds (default: 1 hour) */
  ttlSeconds?: number;
  /** Maximum number of times the key can be used (optional) */
  maxUsage?: number;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
  /** Key prefix (default: "ek_") */
  prefix?: string;
};

export type GeneratedKey = {
  /** The full key to provide to the client (only shown once) */
  key: string;
  /** The key ID for reference */
  id: string;
  /** When the key expires */
  expiresAt: Date;
  /** Scopes granted to the key */
  scopes: string[];
};

export type ValidatedKey = {
  /** Whether the key is valid */
  valid: boolean;
  /** The key record if valid */
  key?: EphemeralKey;
  /** Error message if invalid */
  error?: string;
};

// ============================================================
// Constants
// ============================================================

const DEFAULT_TTL_SECONDS = 60 * 60; // 1 hour
const KEY_BYTE_LENGTH = 32; // 256 bits of entropy
const DEFAULT_PREFIX = "ek_";

// Header name for ephemeral key authentication
export const EPHEMERAL_KEY_HEADER = "x-ephemeral-key";

// ============================================================
// Key Generation
// ============================================================

/**
 * Generate a cryptographically secure random key.
 */
function generateRandomKey(prefix: string = DEFAULT_PREFIX): string {
  const randomBytes = crypto.getRandomValues(new Uint8Array(KEY_BYTE_LENGTH));
  const randomPart = uint8ArrayToBase64Url(randomBytes);
  return `${prefix}${randomPart}`;
}

/**
 * Convert Uint8Array to base64url string.
 */
function uint8ArrayToBase64Url(bytes: Uint8Array): string {
  const base64 = btoa(String.fromCharCode(...bytes));
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/**
 * Convert Uint8Array to hex string.
 */
function uint8ArrayToHex(bytes: Uint8Array): string {
  return Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Hash a key for secure storage.
 * We use SHA-256 since the key already has high entropy.
 */
async function hashKey(key: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(key);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  return uint8ArrayToHex(new Uint8Array(hashBuffer));
}

/**
 * Generate a new ephemeral key and store it in the database.
 *
 * @returns The generated key (only returned once, not stored in plaintext)
 */
export async function generateEphemeralKey(
  options: GenerateKeyOptions = {},
): Promise<GeneratedKey> {
  const {
    name,
    scopes = [],
    userId,
    ttlSeconds = DEFAULT_TTL_SECONDS,
    maxUsage,
    metadata = {},
    prefix = DEFAULT_PREFIX,
  } = options;

  // Generate the key
  const key = generateRandomKey(prefix);
  const keyHash = await hashKey(key);
  const idBytes = crypto.getRandomValues(new Uint8Array(16));
  const id = uint8ArrayToHex(idBytes);
  const expiresAt = new Date(Date.now() + ttlSeconds * 1000);

  // Store in database
  const newKey: NewEphemeralKey = {
    id,
    keyHash,
    prefix,
    name: name ?? null,
    scopes,
    userId: userId ?? null,
    expiresAt,
    maxUsage: maxUsage ?? null,
    metadata,
  };

  await db.insert(ephemeralKey).values(newKey);

  return {
    key,
    id,
    expiresAt,
    scopes,
  };
}

// ============================================================
// Key Validation
// ============================================================

/**
 * Validate an ephemeral key from a request.
 *
 * Checks:
 * - Key exists in database
 * - Key has not expired
 * - Key has not been revoked
 * - Key has not exceeded max usage (if set)
 *
 * If valid, increments the usage counter and updates lastUsedAt.
 */
export async function validateEphemeralKey(key: string): Promise<ValidatedKey> {
  if (!key) {
    return { valid: false, error: "No key provided" };
  }

  const keyHash = await hashKey(key);
  const now = new Date();

  // Find the key
  const [record] = await db
    .select()
    .from(ephemeralKey)
    .where(
      and(
        eq(ephemeralKey.keyHash, keyHash),
        gt(ephemeralKey.expiresAt, now),
        isNull(ephemeralKey.revokedAt),
      ),
    )
    .limit(1);

  if (!record) {
    return { valid: false, error: "Invalid or expired key" };
  }

  // Check max usage
  if (record.maxUsage !== null && record.usageCount >= record.maxUsage) {
    return { valid: false, error: "Key usage limit exceeded" };
  }

  // Update usage stats
  await db
    .update(ephemeralKey)
    .set({
      lastUsedAt: now,
      usageCount: sql`${ephemeralKey.usageCount} + 1`,
    })
    .where(eq(ephemeralKey.id, record.id));

  return {
    valid: true,
    key: record,
  };
}

/**
 * Validate a key without incrementing usage counter.
 * Useful for checking if a key is valid before using it.
 */
export async function peekEphemeralKey(key: string): Promise<ValidatedKey> {
  if (!key) {
    return { valid: false, error: "No key provided" };
  }

  const keyHash = await hashKey(key);
  const now = new Date();

  const [record] = await db
    .select()
    .from(ephemeralKey)
    .where(
      and(
        eq(ephemeralKey.keyHash, keyHash),
        gt(ephemeralKey.expiresAt, now),
        isNull(ephemeralKey.revokedAt),
      ),
    )
    .limit(1);

  if (!record) {
    return { valid: false, error: "Invalid or expired key" };
  }

  if (record.maxUsage !== null && record.usageCount >= record.maxUsage) {
    return { valid: false, error: "Key usage limit exceeded" };
  }

  return { valid: true, key: record };
}

// ============================================================
// Key Management
// ============================================================

/**
 * Revoke an ephemeral key by ID.
 */
export async function revokeEphemeralKey(id: string): Promise<boolean> {
  const result = await db
    .update(ephemeralKey)
    .set({ revokedAt: new Date() })
    .where(and(eq(ephemeralKey.id, id), isNull(ephemeralKey.revokedAt)));

  return result.rowsAffected > 0;
}

/**
 * Revoke all keys for a user.
 */
export async function revokeUserKeys(userId: string): Promise<number> {
  const result = await db
    .update(ephemeralKey)
    .set({ revokedAt: new Date() })
    .where(and(eq(ephemeralKey.userId, userId), isNull(ephemeralKey.revokedAt)));

  return result.rowsAffected;
}

/**
 * Get all active keys for a user.
 */
export async function getUserKeys(userId: string): Promise<EphemeralKey[]> {
  const now = new Date();

  return db
    .select()
    .from(ephemeralKey)
    .where(
      and(
        eq(ephemeralKey.userId, userId),
        gt(ephemeralKey.expiresAt, now),
        isNull(ephemeralKey.revokedAt),
      ),
    )
    .orderBy(ephemeralKey.createdAt);
}

/**
 * Clean up expired keys from the database.
 * Should be run periodically (e.g., daily cron job).
 */
export async function cleanupExpiredKeys(): Promise<number> {
  const now = new Date();

  const result = await db
    .delete(ephemeralKey)
    .where(sql`${ephemeralKey.expiresAt} < ${now}`);

  return result.rowsAffected;
}

/**
 * Check if a key has a specific scope.
 */
export function hasScope(key: EphemeralKey, scope: string): boolean {
  const scopes = key.scopes ?? [];
  return scopes.includes("*") || scopes.includes(scope);
}

/**
 * Check if a key has all specified scopes.
 */
export function hasAllScopes(key: EphemeralKey, requiredScopes: string[]): boolean {
  return requiredScopes.every(scope => hasScope(key, scope));
}

/**
 * Check if a key has any of the specified scopes.
 */
export function hasAnyScope(key: EphemeralKey, scopes: string[]): boolean {
  return scopes.some(scope => hasScope(key, scope));
}
