// Image #49: natural-language schedule composer.
// Header morphs into `[trash] Cancel task scheduling`. Body shows a soft
// frame around the read-only step list, an agent reply bubble asking for
// the cadence, and a chat-style composer at the bottom. On submit we
// hit /workflows/{id}/parse-schedule (aux LLM), surface the parsed
// ScheduleConfig in a confirmation modal (the "always ask permission"
// stand-in for the schedule_workflow tool call), and PATCH on confirm.

import React, { useCallback, useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Dialog from '@mui/material/Dialog';
import TextareaAutosize from '@mui/material/TextareaAutosize';
import DeleteOutlineRounded from '@mui/icons-material/DeleteOutlineRounded';
import { useClaudeTokens } from '@/shared/styles/ThemeContext';
import { useAppDispatch } from '@/shared/hooks';
import { updateWorkflow, updateWorkflowCard, type ScheduleConfig, type Workflow } from '@/shared/state/workflowsSlice';
import StepList from './StepList';
import { API_BASE, getAuthToken } from '@/shared/config';

interface Props {
  workflow: Workflow;
  steps: Workflow['steps'];
}

export default function SchedulingView({ workflow, steps }: Props) {
  const c = useClaudeTokens();
  const dispatch = useAppDispatch();
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<ScheduleConfig | null>(null);

  const onCancel = useCallback(() => {
    dispatch(updateWorkflowCard({ workflowId: workflow.id, patch: { view: 'saved' } }));
  }, [dispatch, workflow.id]);

  const onSubmit = useCallback(async () => {
    if (!draft.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const tok = (() => { try { return getAuthToken(); } catch { return ''; } })();
      const res = await fetch(`${API_BASE}/workflows/${encodeURIComponent(workflow.id)}/parse-schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(tok ? { Authorization: `Bearer ${tok}` } : {}) },
        body: JSON.stringify({ text: draft.trim() }),
      });
      if (!res.ok) {
        setError(`Couldn't parse that. Try "every Wednesday at 1pm" or "Mondays at 3pm".`);
        return;
      }
      const data = await res.json();
      const cfg = data?.schedule as ScheduleConfig | undefined;
      if (!cfg) {
        setError(`Couldn't read a schedule out of that. Try being more specific.`);
        return;
      }
      setPending(cfg);
    } catch (e) {
      setError((e as Error)?.message || 'Network error.');
    } finally {
      setBusy(false);
    }
  }, [draft, busy, workflow.id]);

  const onConfirm = useCallback(async () => {
    if (!pending) return;
    setBusy(true);
    try {
      await dispatch(updateWorkflow({
        id: workflow.id,
        patch: { schedule: { ...pending, enabled: true } as Workflow['schedule'] },
        ifMatch: workflow.updated_at || null,
      }));
      dispatch(updateWorkflowCard({ workflowId: workflow.id, patch: { view: 'saved' } }));
    } finally {
      setBusy(false);
      setPending(null);
    }
  }, [pending, dispatch, workflow.id, workflow.updated_at]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25, minHeight: '100%' }}>
      {/* Inline header replacement. The default History/Run row is hidden
          for 'scheduling' view; this Cancel button sits in its place. */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Box
          onClick={onCancel}
          role="button"
          sx={{
            display: 'inline-flex', alignItems: 'center', gap: 0.45,
            fontSize: '0.82rem', fontWeight: 600,
            color: c.text.secondary, cursor: 'pointer',
            px: 0.75, py: 0.5,
            '&:hover': { color: c.status.error },
          }}>
          <DeleteOutlineRounded sx={{ fontSize: 16 }} />
          Cancel task scheduling
        </Box>
      </Box>
      <Box sx={{
        p: 1.5, borderRadius: `${c.radius.lg}px`,
        border: `1px solid ${c.border.subtle}`, bgcolor: c.bg.elevated,
      }}>
        <StepList steps={steps} />
      </Box>
      <Box sx={{
        p: 1.5, borderRadius: `${c.radius.lg}px`,
        bgcolor: c.bg.surface,
        border: `1px solid ${c.border.subtle}`,
      }}>
        <Typography sx={{ fontSize: '0.92rem', color: c.text.primary, lineHeight: 1.45 }}>
          When should this workflow run (e.g. every Wednesday at 1pm)
        </Typography>
      </Box>
      {error && (
        <Typography sx={{ fontSize: '0.82rem', color: c.status.error }}>{error}</Typography>
      )}
      <Box sx={{ flex: 1 }} />
      <Box sx={{
        p: 1, borderRadius: `${c.radius.lg}px`,
        border: `1px solid ${c.border.subtle}`, bgcolor: c.bg.surface,
        display: 'flex', flexDirection: 'column', gap: 0.5,
      }}>
        <TextareaAutosize
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              void onSubmit();
            }
          }}
          minRows={1}
          maxRows={4}
          placeholder="Agent, @ for context, / for commands"
          style={{
            width: '100%', resize: 'none', boxSizing: 'border-box',
            fontFamily: 'inherit', fontSize: '0.92rem', color: c.text.primary,
            border: 'none', outline: 'none', background: 'transparent',
            padding: '6px 4px', lineHeight: 1.45,
          }}
        />
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Pill label="Agent" />
          <Pill label="Claude Opus 4.6" />
          <Pill label="High" />
          <Box sx={{ flex: 1 }} />
          <Box
            onClick={onSubmit}
            role="button"
            sx={{
              fontSize: '0.78rem', fontWeight: 700,
              color: '#fff', bgcolor: c.accent.primary,
              px: 1.2, py: 0.4, borderRadius: 999,
              cursor: busy || !draft.trim() ? 'not-allowed' : 'pointer',
              opacity: busy || !draft.trim() ? 0.5 : 1,
              '&:hover': { filter: 'brightness(1.05)' },
            }}>
            {busy ? 'Working…' : 'Send'}
          </Box>
        </Box>
      </Box>

      <Dialog open={!!pending} onClose={() => setPending(null)}>
        <Box sx={{ p: 2.5, minWidth: 360, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          <Typography sx={{ fontSize: '1rem', fontWeight: 700, color: c.text.primary }}>
            Schedule this workflow?
          </Typography>
          <Typography sx={{ fontSize: '0.9rem', color: c.text.secondary, lineHeight: 1.5 }}>
            The agent wants to set <b>{workflow.title}</b> to run <b>{pending && describe(pending)}</b>. You can change or cancel this anytime.
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 0.5 }}>
            <Box
              onClick={() => setPending(null)}
              role="button"
              sx={{ fontSize: '0.86rem', color: c.text.secondary, px: 1, py: 0.6, cursor: 'pointer', '&:hover': { color: c.text.primary } }}>
              Cancel
            </Box>
            <Box
              onClick={onConfirm}
              role="button"
              sx={{
                fontSize: '0.86rem', fontWeight: 700,
                color: '#fff', bgcolor: c.accent.primary,
                px: 1.4, py: 0.55, borderRadius: 999, cursor: 'pointer',
                '&:hover': { filter: 'brightness(1.05)' },
              }}>
              {busy ? 'Applying…' : 'Schedule it'}
            </Box>
          </Box>
        </Box>
      </Dialog>
    </Box>
  );
}

function Pill({ label }: { label: string }) {
  const c = useClaudeTokens();
  return (
    <Box sx={{
      fontSize: '0.74rem', fontWeight: 600, color: c.text.secondary,
      px: 0.8, py: 0.25, borderRadius: 999,
      border: `1px solid ${c.border.subtle}`,
    }}>{label}</Box>
  );
}

function describe(s: ScheduleConfig): string {
  const h12 = ((s.hour + 11) % 12) + 1;
  const ampm = s.hour < 12 ? 'am' : 'pm';
  const time = s.minute === 0 ? `${h12}${ampm}` : `${h12}:${String(s.minute).padStart(2, '0')}${ampm}`;
  if (s.repeat_unit === 'day') return s.repeat_every === 1 ? `every day at ${time}` : `every ${s.repeat_every} days at ${time}`;
  if (s.repeat_unit === 'month') return s.repeat_every === 1 ? `every month at ${time}` : `every ${s.repeat_every} months at ${time}`;
  const labels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  if (s.on_days.length === 5 && [1,2,3,4,5].every((d) => s.on_days.includes(d))) return `weekdays at ${time}`;
  if (s.on_days.length === 2 && [0,6].every((d) => s.on_days.includes(d))) return `weekends at ${time}`;
  if (s.on_days.length === 1) return `${labels[s.on_days[0]]}s at ${time}`;
  return `weekly at ${time}`;
}
