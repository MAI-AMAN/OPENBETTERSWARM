import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import type { ClaudeTokens } from '@/shared/styles/claudeTokens';
import ChatBubbleTeardrop from '../ChatBubbleTeardrop';

const DashboardEmptyState: React.FC<{ c: ClaudeTokens }> = ({ c }) => (
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
    <Typography sx={{ color: c.text.tertiary, fontSize: '1.1rem', mb: 1 }}>
      No agents running
    </Typography>
    <Typography
      sx={{
        fontSize: '0.9rem',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 0.7,
        color: c.text.primary,
      }}
    >
      Click the
      <Box component="span" sx={{ display: 'inline-flex', color: c.text.tertiary }}>
        <ChatBubbleTeardrop sx={{ fontSize: 15 }} />
      </Box>
      below to launch your first agent
    </Typography>
  </Box>
);

export default DashboardEmptyState;
