// Sign-in gate. Shown post-onboarding to users without an active identity:
//   - User signed out from Settings, gate appears so they can sign back in.
//   - Existing v1.0.28 user upgrading to v1.0.29 with no user_id yet (the
//     soft-gate grace window applies; see SignInGateLoader in Main.tsx).
//
// Fresh first-launch users go through OnboardingModal instead — its first
// step is sign-in, this gate stays hidden in that path.
//
// Path: "Continue with Google" → shell.openExternal opens the cloud's
// /api/auth/google/start. Cloud handles the round-trip and serves a
// bearer-handoff page that POSTs the bearer to the local backend's
// /api/auth/signin-activate. After the bearer lands, settings.user_id
// flips non-null and the gate self-dismisses (SignInGateLoader's poll
// picks up the change within ~2s).

import React from 'react';
import {
  Box,
  Typography,
  Modal,
  Button,
  Link,
} from '@mui/material';
import GoogleIcon from '@mui/icons-material/Google';
import { useAppSelector } from '@/shared/hooks';
import { useClaudeTokens } from '@/shared/styles/ThemeContext';
import { OPENSWARM_DEFAULT_PROXY_URL } from '@/shared/config';
import { report } from '@/shared/serviceClient';

interface SignInGateProps {
  /** Soft gate adds a "Skip for now" link; hard gate omits it. */
  softGate: boolean;
  onSkip?: () => void;
}

export default function SignInGate({ softGate, onSkip }: SignInGateProps): JSX.Element {
  const tokens = useClaudeTokens();
  const proxyUrl = useAppSelector(
    (s) => s.settings.data.openswarm_proxy_url || OPENSWARM_DEFAULT_PROXY_URL,
  );
  const installId = useAppSelector((s) => s.settings.data.installation_id ?? '');

  const onGoogle = () => {
    report('signin', 'google_clicked');
    // Pass local_port so the cloud's bearer-handoff page POSTs to this
    // exact backend port. Without it, the page falls back to probing
    // 8324..8328 — which fails for users whose machines have those ports
    // occupied (Electron picks the first free port in 8324..8424).
    const localPort = (window as any).__OPENSWARM_PORT__ || 8324;
    const params = new URLSearchParams({
      install_id: installId,
      local_port: String(localPort),
    });
    const startUrl =
      proxyUrl.replace(/\/$/, '') +
      '/api/auth/google/start?' + params.toString();
    const api = (window as any).openswarm;
    if (api?.openExternal) {
      api.openExternal(startUrl);
    } else {
      window.open(startUrl, '_blank');
    }
  };

  return (
    <Modal
      open
      disableEscapeKeyDown={!softGate}
      hideBackdrop={false}
      sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      slotProps={{ backdrop: { sx: { backgroundColor: 'rgba(0,0,0,0.55)' } } }}
    >
      <Box
        sx={{
          width: '100%',
          maxWidth: 440,
          mx: 2,
          backgroundColor: tokens.bg.surface,
          color: tokens.text.primary,
          border: `1px solid ${tokens.border.subtle}`,
          borderRadius: 3,
          p: 4,
          textAlign: 'center',
          outline: 'none',
        }}
      >
        <Typography
          variant="h5"
          sx={{ fontFamily: '"Charter", Georgia, serif', fontWeight: 500, mb: 1 }}
        >
          Sign in to OpenSwarm
        </Typography>
        <Typography
          variant="body2"
          sx={{ color: tokens.text.muted, mb: 3, lineHeight: 1.5 }}
        >
          Sign in lets us sync your settings and back up your data.
        </Typography>

        <Button
          fullWidth
          variant="contained"
          size="large"
          startIcon={<GoogleIcon />}
          onClick={onGoogle}
          sx={{
            py: 1.4,
            backgroundColor: tokens.text.primary,
            color: tokens.text.inverse,
            textTransform: 'none',
            fontSize: 15,
            fontWeight: 500,
            '&:hover': { backgroundColor: tokens.text.primary, opacity: 0.9 },
          }}
        >
          Continue with Google
        </Button>

        {softGate && onSkip && (
          <Box sx={{ mt: 3, pt: 2, borderTop: `1px solid ${tokens.border.subtle}` }}>
            <Link
              component="button"
              onClick={() => {
                report('signin', 'gate_skipped');
                onSkip();
              }}
              sx={{ fontSize: 12, color: tokens.text.muted, textDecoration: 'none' }}
            >
              Skip for now — I'll sign in later
            </Link>
          </Box>
        )}
      </Box>
    </Modal>
  );
}
