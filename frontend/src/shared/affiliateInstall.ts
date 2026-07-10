const APP_INSTALL_ID_RE = /^[A-Za-z0-9_-]{8,128}$/;

export async function getAffiliateAppInstallId(): Promise<string | null> {
  try {
    const api = (window as any).openswarm;
    const state = await api?.getInstallState?.();
    const appInstallId = state && typeof state.app_install_id === 'string'
      ? state.app_install_id
      : '';
    return APP_INSTALL_ID_RE.test(appInstallId) ? appInstallId : null;
  } catch {
    return null;
  }
}
