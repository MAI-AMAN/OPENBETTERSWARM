import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import type { ClaudeTokens } from '@/shared/styles/claudeTokens';
import { useDashboardActive } from '@/shared/hooks/useDashboardActive';
import ChatBubbleTeardrop from '../ChatBubbleTeardrop';

const DashboardEmptyState: React.FC<{ c: ClaudeTokens }> = ({ c }) => {
  // The host hides Dashboard with visibility:hidden (not display:none), which keeps
  // CSS animations ticking; gate on active so the shimmer only burns while watched.
  const active = useDashboardActive();
  return (
    <Box
      sx={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        pointerEvents: 'none',
      }}
    >
      <style>{`@keyframes empty-state-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }`}</style>
      <Typography sx={{ color: c.text.tertiary, fontSize: '1.1rem', mb: 1 }}>
        No agents running
      </Typography>
      <Typography
        sx={{
          fontSize: '0.9rem',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 0.7,
          background: `linear-gradient(90deg, ${c.text.ghost} 0%, ${c.text.ghost} 40%, ${c.text.primary} 50%, ${c.text.ghost} 60%, ${c.text.ghost} 100%)`,
          backgroundSize: '200% 100%',
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          color: 'transparent',
          animation: active ? 'empty-state-shimmer 6s linear infinite' : 'none',
        }}
      >
        Click the
        {/* Literal toolbar glyph; the shimmer's transparent color would hide it, so reset color here. */}
        <Box component="span" sx={{ display: 'inline-flex', color: c.text.tertiary }}>
          <ChatBubbleTeardrop sx={{ fontSize: 15 }} />
        </Box>
        below to launch your first agent
      </Typography>
    </Box>
  );
};

export default DashboardEmptyState;
