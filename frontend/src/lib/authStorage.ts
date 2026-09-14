const TOKEN_KEY = "reconcile.access_token";

/**
 * Thin wrapper around localStorage for the JWT. A dedicated module (rather
 * than scattering localStorage calls) is the seam that lets auth state
 * broadcast across tabs via the `storage` event, and gives one place to
 * swap persistence strategy later.
 */
export const authStorage = {
  get(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  set(token: string) {
    localStorage.setItem(TOKEN_KEY, token);
    window.dispatchEvent(new Event("reconcile:auth-changed"));
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new Event("reconcile:auth-changed"));
  },
};
