import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';
import type { ClaudeTokens } from '@/shared/styles/claudeTokens';
import { STARTER_CATEGORIES } from '@/shared/starterCategories';

const GREETING = "Hi, I'm your AI team. What do you want done?";

// One-shot typewriter for a fixed string (no infinite loop; stops at the end). startDelayMs
// holds the start so the header title can stream first (sequential reveal).
function useTypewriter(text: string, speedMs = 45, startDelayMs = 0): { shown: string; done: boolean } {
  const [shown, setShown] = React.useState('');
  React.useEffect(() => {
    setShown('');
    let interval: number | undefined;
    const startTimer = window.setTimeout(() => {
      let i = 0;
      interval = window.setInterval(() => {
        i += 1;
        setShown(text.slice(0, i));
        if (i >= text.length) window.clearInterval(interval);
      }, speedMs);
    }, startDelayMs);
    return () => { window.clearTimeout(startTimer); if (interval) window.clearInterval(interval); };
  }, [text, speedMs, startDelayMs]);
  return { shown, done: shown.length >= text.length };
}

// The first-run welcome: the greeting streams in like typing, then the quick-reply chips
// pop in (staggered). Two-level: category -> concrete prompts. Research/Write/Learn -> onPick
// (real run); Build -> onPickBuilder (App Builder). Pure UI; no run until the parent fires.
const WelcomeQuickReplies: React.FC<{
  c: ClaudeTokens;
  onPick: (prompt: string) => void;
  onPickBuilder: (prompt: string) => void;
}> = ({ c, onPick, onPickBuilder }) => {
  // Slow + delayed so it reads as a sequence: card pops, the header title streams, THEN
  // the greeting types, THEN the chips pop in.
  const { shown: greeting, done: greetingDone } = useTypewriter(GREETING, 46, 650);
  const [expanded, setExpanded] = React.useState<string | null>(null);
  const currentCategory = STARTER_CATEGORIES.find((cat) => cat.id === expanded);
  const isAppBuilder = currentCategory?.target === 'app-builder';
  const currentPrompts = currentCategory?.prompts ?? [];

  const pick = (prompt: string) => {
    if (isAppBuilder) onPickBuilder(prompt);
    else onPick(prompt);
  };

  return (
    <Box sx={{ px: 1.5, pt: 1.5, pb: 1, width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
      {/* Greeting bubble, typed out like a real reply. */}
      <Box
        sx={{
          maxWidth: '88%',
          px: 1.6, py: 1.1, mb: 1.8,
          borderRadius: '4px 14px 14px 14px',
          border: `1px solid ${c.border.subtle}`,
          background: c.bg.surface,
          color: c.text.primary,
          fontSize: '0.98rem',
          minHeight: '1.4rem',
        }}
      >
        {greeting}
        {!greetingDone && (
          <Box component="span" sx={{ ml: '1px', color: c.accent.primary }}>▌</Box>
        )}
      </Box>

      {/* Chips reveal only once the greeting finishes, each popping in with a stagger. */}
      {greetingDone && (
        <Box sx={{ width: '100%', alignSelf: 'stretch' }}>
          <AnimatePresence mode="wait" initial={false}>
            {expanded === null ? (
              <motion.div key="categories" initial={false} style={{ display: 'flex', flexDirection: 'column' }}>
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.2 }}>
                  <Typography sx={{ color: c.text.ghost, fontSize: '0.82rem', mb: 1 }}>
                    pick one, or just type below
                  </Typography>
                </motion.div>
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                  {STARTER_CATEGORIES.map((cat, i) => (
                    <motion.button
                      key={cat.id}
                      onClick={() => setExpanded(cat.id)}
                      initial={{ opacity: 0, scale: 0.82 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ type: 'spring', stiffness: 420, damping: 22, delay: 0.18 + i * 0.14 }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        padding: '10px 14px',
                        borderRadius: 13,
                        border: `1px solid ${c.border.medium}`,
                        background: c.bg.surface,
                        color: c.text.secondary,
                        fontSize: '0.9rem', fontWeight: 500,
                        cursor: 'pointer', fontFamily: 'inherit',
                      }}
                    >
                      <cat.Icon size={16} />
                      {cat.label}
                    </motion.button>
                  ))}
                </Box>
              </motion.div>
            ) : (
              <motion.div
                key="specifics"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.18 }}
                style={{ display: 'flex', flexDirection: 'column' }}
              >
                <Box
                  component="button"
                  onClick={() => setExpanded(null)}
                  sx={{
                    display: 'inline-flex', alignItems: 'center', gap: 0.5,
                    alignSelf: 'flex-start', mb: 0.9, px: 0.6, py: 0.3,
                    border: 'none', background: 'transparent',
                    color: c.text.ghost, fontSize: '0.85rem',
                    cursor: 'pointer', fontFamily: 'inherit',
                    '&:hover': { color: c.text.secondary },
                  }}
                >
                  <ArrowLeft size={14} /> back
                </Box>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.7 }}>
                  {currentPrompts.map((prompt, i) => (
                    <motion.button
                      key={prompt}
                      onClick={() => pick(prompt)}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ type: 'spring', stiffness: 520, damping: 26, delay: i * 0.05 }}
                      style={{
                        textAlign: 'left',
                        padding: '9px 14px',
                        borderRadius: 11,
                        border: `1px solid ${c.border.medium}`,
                        background: c.bg.surface,
                        color: c.text.secondary,
                        fontSize: '0.88rem',
                        cursor: 'pointer', fontFamily: 'inherit',
                      }}
                    >
                      {prompt}
                    </motion.button>
                  ))}
                </Box>
              </motion.div>
            )}
          </AnimatePresence>
        </Box>
      )}
    </Box>
  );
};

export default WelcomeQuickReplies;
