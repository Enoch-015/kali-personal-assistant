// server/utils/vault.ts
import vault from 'node-vault'

/**
 This module provides a VaultClient class to interact with HashiCorp Vault for secure
 secret management. It supports authentication via AppRole, reading, writing,
 deleting, and listing secrets, as well as caching for performance.
*/

interface VaultConfig {
  addr: string
  roleId: string
  secretId: string
}

interface VaultSecret {
  [key: string]: any
}

class VaultClient {
  private client: any = null
  private token: string | undefined = undefined
  private tokenExpiry: number = 0
  private secretsCache: Map<string, { data: VaultSecret; expiry: number }> = new Map()
  private config: VaultConfig

  constructor(config: VaultConfig) {
    this.config = config
  }

  /**
   * Authenticate with Vault using AppRole
   */
  private async authenticate(): Promise<void> {
    const tempClient = vault({
      apiVersion: 'v1',
      endpoint: this.config.addr
    })

    try {
      const result = await tempClient.approleLogin({
        role_id: this.config.roleId,
        secret_id: this.config.secretId
      })

      this.token = result.auth.client_token
      this.tokenExpiry = Date.now() + (result.auth.lease_duration * 1000)

      this.client = vault({
        apiVersion: 'v1',
        endpoint: this.config.addr,
        token: this.token
      })

      console.log('Vault authentication successful')
    } catch (error) {
      console.error('Vault authentication failed:', error)
      throw new Error('Failed to authenticate with Vault')
    }
  }

  /**
   * Ensure we have a valid token
   */
  private async ensureAuthenticated(): Promise<void> {
    // Check if token exists and is not expired (with 5 min buffer)
    if (!this.client || Date.now() > (this.tokenExpiry - 300000)) {
      await this.authenticate()
    }
  }

  /**
   * Read a secret from Vault
   * @param path - Secret path (e.g., 'nuxt', 'python-ai')
   * @param useCache - Whether to use cached value
   */
  async getSecret(path: string, useCache: boolean = true): Promise<VaultSecret> {
    const fullPath = `secret/data/${path}`
    const now = Date.now()

    // Check cache (5 min TTL)
    if (useCache) {
      const cached = this.secretsCache.get(path)
      if (cached && now < cached.expiry) {
        return cached.data
      }
    }

    await this.ensureAuthenticated()

    try {
      const result = await this.client.read(fullPath)
      const secretData = result.data.data

      // Cache the secret
      this.secretsCache.set(path, {
        data: secretData,
        expiry: now + (5 * 60 * 1000) // 5 minutes
      })

      return secretData
    } catch (error: any) {
      console.error(`Failed to read secret from ${path}:`, error.message)
      throw new Error(`Failed to read secret: ${error.message}`)
    }
  }

  /**
   * Write a secret to Vault
   * @param path - Secret path
   * @param data - Secret data to write
   */
  async setSecret(path: string, data: VaultSecret): Promise<void> {
    const fullPath = `secret/data/${path}`

    await this.ensureAuthenticated()

    try {
      await this.client.write(fullPath, { data })
      
      // Invalidate cache
      this.secretsCache.delete(path)
      
      console.log(`Secret written to ${path}`)
    } catch (error: any) {
      console.error(`Failed to write secret to ${path}:`, error.message)
      throw new Error(`Failed to write secret: ${error.message}`)
    }
  }

  /**
   * Delete a secret from Vault
   * @param path - Secret path
   */
  async deleteSecret(path: string): Promise<void> {
    const fullPath = `secret/metadata/${path}`

    await this.ensureAuthenticated()

    try {
      await this.client.delete(fullPath)
      
      // Invalidate cache
      this.secretsCache.delete(path)
      
      console.log(`Secret deleted from ${path}`)
    } catch (error: any) {
      console.error(`Failed to delete secret from ${path}:`, error.message)
      throw new Error(`Failed to delete secret: ${error.message}`)
    }
  }

  /**
   * List all secrets under a path
   * @param path - Base path to list
   */
  async listSecrets(path: string = ''): Promise<string[]> {
    const fullPath = path ? `secret/metadata/${path}` : 'secret/metadata'

    await this.ensureAuthenticated()

    try {
      const result = await this.client.list(fullPath)
      return result.data.keys || []
    } catch (error: any) {
      console.error(`Failed to list secrets at ${path}:`, error.message)
      return []
    }
  }

  /**
   * Clear the secrets cache
   */
  clearCache(): void {
    this.secretsCache.clear()
    console.log('Vault cache cleared')
  }

  /**
   * Get specific secret key
   * @param path - Secret path
   * @param key - Specific key to retrieve
   */
  async getSecretKey(path: string, key: string): Promise<any> {
    const secrets = await this.getSecret(path)
    return secrets[key]
  }
}

// Singleton instance
let vaultClientInstance: VaultClient | null = null

/**
 * Get the Vault client instance
 */
export function getVaultClient(): VaultClient {
  if (!vaultClientInstance) {
    const config = useRuntimeConfig()
    
    if (!config.vaultAddr || !config.vaultRoleId || !config.vaultSecretId) {
      throw new Error('Vault configuration missing. Check environment variables.')
    }

    vaultClientInstance = new VaultClient({
      addr: config.vaultAddr,
      roleId: config.vaultRoleId,
      secretId: config.vaultSecretId
    })
  }

  return vaultClientInstance
}

/**
 * Convenience function to get Nuxt secrets
 */
export async function getNuxtSecrets() {
  const client = getVaultClient()
  return await client.getSecret('nuxt')
}

/**
 * Convenience function to get shared secrets
 */
export async function getSharedSecrets() {
  const client = getVaultClient()
  return await client.getSecret('shared')
}

/**
 * Convenience function to get LiveKit secrets
 */
export async function getLiveKitSecrets() {
  const client = getVaultClient()
  return await client.getSecret('livekit')
}