import { report } from '@/shared/serviceClient';

export type OpenSwarmPlan = 'pro' | 'pro_plus' | 'ultra';
export type BillingInterval = 'monthly' | 'annual';
export type CheckoutSource = 'settings' | 'onboarding' | 'upgrade_cta';

interface SubscribeOptions {
  wasSubscribed?: boolean;
}

// Kicks off a Stripe Checkout session for the given plan + interval and opens
// the returned URL in the user's default browser (or a new tab fallback).
// All subscribe CTAs across Settings, Onboarding, and the 429 error card go
// through this helper so the wire shape and error handling stay consistent.
export async function subscribeToPlan(
  plan: OpenSwarmPlan,
  billingInterval: BillingInterval,
  source: CheckoutSource,
  opts: SubscribeOptions = {},
): Promise<void> {
  report('subscription', 'subscribe_clicked', {
    source,
    plan,
    billing_interval: billingInterval,
    was_subscribed: !!opts.wasSubscribed,
  });

  try {
    // Cloud schema uses "yearly"; the desktop UI uses "annual".
    // Normalize at the boundary so the rest of the client stays consistent.
    const wireInterval = billingInterval === 'annual' ? 'yearly' : billingInterval;

    // Pull app_install_id from Electron's persisted install.json so the cloud
    // can join Stripe checkout against install_tokens for affiliate payout
    // attribution. Best-effort: missing IPC (renderer running outside the
    // shell, e.g. in a dev browser) just means no attribution, not an error.
    let appInstallId: string | null = null;
    try {
      const api = (window as any).openswarm;
      const state = await api?.getInstallState?.();
      if (state && typeof state.app_install_id === 'string') {
        appInstallId = state.app_install_id;
      }
    } catch {}

    const body: Record<string, unknown> = { plan, billing_interval: wireInterval };
    if (appInstallId) body.app_install_id = appInstallId;

    const r = await fetch('https://api.openswarm.com/api/stripe/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      console.error(`Checkout request failed: ${r.status}`);
      return;
    }
    const { url } = await r.json();
    if (!url) return;

    report('subscription', 'checkout_opened', {
      source,
      plan,
      billing_interval: billingInterval,
    });

    const api = (window as any).openswarm;
    if (api?.openExternal) api.openExternal(url);
    else window.open(url, '_blank');
  } catch (e) {
    console.error('Failed to create checkout session:', e);
  }
}
