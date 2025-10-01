// Minimal client shape; avoid importing non-exported types from better-auth
type PossibleAuthClient = {
  getSession?: () => Promise<any>;
  [k: string]: any;
};

// Define the session response type
type SessionResponse = {
  user: any;
  session?: any;
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
        const { data } = await useFetch<SessionResponse>("/api/auth/get-session");
        user.value = data.value?.user ?? null;
      }
    }
    finally {
      loading.value = false;
    }
  }

  return { authClient, user, loading, refreshSession };
}
