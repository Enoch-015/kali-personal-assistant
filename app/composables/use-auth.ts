// Minimal client shape; avoid importing non-exported types from better-auth
type PossibleAuthClient = {
  getSession?: () => Promise<any>;
  [k: string]: any;
};

export function useAuth() {
  const nuxtApp = useNuxtApp();
  const authClient = nuxtApp.$authClient as PossibleAuthClient | undefined;
  const user = useState<any>("auth:user", () => null);
  const loading = useState<boolean>("auth:loading", () => false);

  async function refreshSession() {
    try {
      loading.value = true;
      if (authClient?.getSession) {
        const ses = await authClient.getSession();
        user.value = ses?.user ?? null;
      }
      else {
        const data: any = await $fetch("/api/auth/session");
        user.value = data?.user ?? null;
      }
    }
    finally {
      loading.value = false;
    }
  }

  return { authClient, user, loading, refreshSession };
}
