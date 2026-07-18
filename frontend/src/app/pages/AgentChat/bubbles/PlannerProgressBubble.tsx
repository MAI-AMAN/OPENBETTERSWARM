import React from 'react';
import { usePlannerStatus } from '@/shared/state/streamingSlice';
import { Box, Typography, CircularProgress, Paper } from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  sessionId: string;
}

const PlannerProgressBubble: React.FC<Props> = ({ sessionId }) => {
  const status = usePlannerStatus(sessionId);

  return (
    <AnimatePresence>
      {status && (
        <motion.div
          initial={{ opacity: 0, y: 10, height: 0 }}
          animate={{ opacity: 1, y: 0, height: 'auto' }}
          exit={{ opacity: 0, y: -10, height: 0 }}
          style={{ overflow: 'hidden', paddingBottom: '16px' }}
        >
          <Paper
            elevation={0}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 2,
              px: 3,
              py: 2,
              borderRadius: 3,
              bgcolor: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              maxWidth: 'fit-content'
            }}
          >
            <CircularProgress size={20} sx={{ color: '#4caf50' }} />
            <Box>
              <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 600, letterSpacing: '0.5px' }}>
                {status.step.replace(/_/g, ' ')}
              </Typography>
              <Typography variant="body1" sx={{ color: 'text.primary', fontWeight: 500 }}>
                {status.message}
              </Typography>
            </Box>
          </Paper>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default PlannerProgressBubble;
