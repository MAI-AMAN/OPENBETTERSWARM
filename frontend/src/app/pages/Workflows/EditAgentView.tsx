// Image #38: Edit Agent chat shell embedded inside the workflow card.
// Header is { Discard | Save }. Body shows a soft frame around the step
// list, then the conversation (agent reply bubbles + tool-call cards +
// user bubbles), then a composer at the bottom. Submitting a message
// hits /workflows/{id}/edit-step which uses aux LLM to propose a step
// edit. The user reviews the proposal, then either applies it to the
// draft (local) or asks the agent to try again. Save persists the
// accumulated draft via PATCH; Discard reverts to the saved state.
//
// Test Agent (Image #39) integration lands in slice 5; the "Test" button
// here is wired but the spawned sibling currently runs the saved workflow
// (not the unsaved draft) until the run endpoint accepts step overrides.

import React, { useCallback, useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Dialog from '@mui/material/Dialog';
import TextareaAutosize from '@mui/material/TextareaAutosize';
import DeleteOutlineRounded from '@mui/icons-material/DeleteOutlineRounded';
import SaveOutlinedIcon from '@mui/icons-material/SaveOutlined';
import PlayArrowRounded from '@mui/icons-material/PlayArrowRounded';
import BuildRounded from '@mui/icons-material/BuildRounded';
import { useClaudeTokens } from '@/shared/styles/ThemeContext';
import { useAppDispatch, useAppSelector } from '@/shared/hooks';
import { clearFixSeed, updateWorkflow, updateWorkflowCard, type Workflow } from '@/shared/state/workflowsSlice';
import StepList from './StepList';
import { API_BASE, getAuthToken } from '@/shared/config';

interface Props {
  workflow: Workflow;
  steps: Workflow['steps'];
  isFixMode?: boolean;
}

type Turn =
  | { kind: 'user'; text: string }
  | { kind: 'assistant'; text: string }
  | { kind: 'proposal'; stepIdx: number; before: string; after: string; explanation: string; applied: boolean }
  | { kind: 'fix-prefix'; stepIdx: number; stepLabel: string; error: string };

export default function EditAgentView({ workflow, steps, isFixMode = false }: Props) {
  const c = useClaudeTokens();
  const dispatch = useAppDispatch();
  const card = useAppSelector((s) => s.workflows.openCards[workflow.id]);
  const fixSeed = card?.fixSeed || null;

  const [draftSteps, setDraftSteps] = useState<Workflow['steps']>(steps);
  const [turns, setTurns] = useState<Turn[]>(() => isFixMode && fixSeed ? [
    { kind: 'fix-prefix', stepIdx: fixSeed.stepIdx, stepLabel: fixSeed.stepLabel, error: fixSeed.error },
  ] : [
    { kind: 'assistant', text: 'How would you like to modify the workflow (e.g. filter out spam emails before summarizing)' },
  ]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);

  useEffect(() => () => { dispatch(clearFixSeed(workflow.id)); }, [dispatch, workflow.id]);

  const dirty = React.useMemo(() => {
    if (draftSteps.length !== steps.length) return true;
    for (let i = 0; i < steps.length; i++) {
      if ((draftSteps[i]?.text || '') !== (steps[i]?.text || '')) return true;
      if ((draftSteps[i]?.label || '') !== (steps[i]?.label || '')) return true;
    }
    return false;
  }, [draftSteps, steps]);

  const onSubmit = useCallback(async () => {
    const text = draft.trim();
    if (!text || busy) return;
    setBusy(true);
    setTurns((t) => [...t, { kind: 'user', text }]);
    setDraft('');
    try {
      const tok = (() => { try { return getAuthToken(); } catch { return ''; } })();
      const res = await fetch(`${API_BASE}/workflows/${encodeURIComponent(workflow.id)}/propose-edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(tok ? { Authorization: `Bearer ${tok}` } : {}) },
        body: JSON.stringify({
          message: text,
          steps: draftSteps.map((s) => ({ id: s.id, text: s.text, label: s.label || null })),
          context: isFixMode && fixSeed ? { failed_step: fixSeed.stepIdx, error: fixSeed.error } : null,
        }),
      });
      if (!res.ok) {
        setTurns((t) => [...t, { kind: 'assistant', text: `Sorry, that didn't go through. (${res.status})` }]);
        return;
      }
      const data = await res.json();
      if (data?.reply) setTurns((t) => [...t, { kind: 'assistant', text: data.reply as string }]);
      if (typeof data?.step_idx === 'number' && typeof data?.new_text === 'string') {
        setTurns((t) => [...t, {
          kind: 'proposal',
          stepIdx: data.step_idx,
          before: draftSteps[data.step_idx]?.text || '',
          after: data.new_text,
          explanation: data.explanation || '',
          applied: false,
        }]);
      }
    } catch (e) {
      setTurns((t) => [...t, { kind: 'assistant', text: (e as Error)?.message || 'Network error.' }]);
    } finally {
      setBusy(false);
    }
  }, [draft, busy, workflow.id, draftSteps, isFixMode, fixSeed]);

  const onApplyProposal = useCallback((turnIdx: number) => {
    setTurns((all) => {
      const next = all.slice();
      const turn = next[turnIdx];
      if (turn?.kind !== 'proposal' || turn.applied) return all;
      setDraftSteps((ds) => {
        const updated = ds.slice();
        if (updated[turn.stepIdx]) {
          updated[turn.stepIdx] = { ...updated[turn.stepIdx], text: turn.after };
        }
        return updated;
      });
      next[turnIdx] = { ...turn, applied: true };
      return next;
    });
  }, []);

  const onDiscard = useCallback(() => {
    if (dirty) {
      // No second confirm; the agent's proposals weren't persisted yet.
      // Reverting just clears local state.
    }
    dispatch(updateWorkflowCard({ workflowId: workflow.id, patch: { view: 'saved' } }));
  }, [dirty, dispatch, workflow.id]);

  const onSaveClick = useCallback(() => {
    if (!dirty) {
      dispatch(updateWorkflowCard({ workflowId: workflow.id, patch: { view: 'saved' } }));
      return;
    }
    setShowSaveModal(true);
  }, [dirty, dispatch, workflow.id]);

  const onConfirmSave = useCallback(async () => {
    setBusy(true);
    try {
      await dispatch(updateWorkflow({
        id: workflow.id,
        patch: { steps: draftSteps },
        ifMatch: workflow.updated_at || null,
      }));
      dispatch(updateWorkflowCard({ workflowId: workflow.id, patch: { view: 'saved' } }));
    } finally {
      setBusy(false);
      setShowSaveModal(false);
    }
  }, [dispatch, workflow.id, workflow.updated_at, draftSteps]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25, minHeight: '100%' }}>
      {/* Inline header replacement. The card's default action bar is
          hidden for edit_agent / fix_agent views. */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box sx={{ flex: 1 }} />
        <HeaderBtn
          label="Discard"
          icon={<DeleteOutlineRounded sx={{ fontSize: 16 }} />}
          onClick={onDiscard}
          tone="muted"
        />
        <HeaderBtn
          label={busy ? 'Saving…' : 'Save'}
          icon={<SaveOutlinedIcon sx={{ fontSize: 16 }} />}
          onClick={onSaveClick}
          tone="filled"
          disabled={busy}
        />
      </Box>
      <Box sx={{
        p: 1.5, borderRadius: `${c.radius.lg}px`,
        border: `1px solid ${c.border.subtle}`, bgcolor: c.bg.elevated,
      }}>
        <StepList steps={draftSteps} />
      </Box>
      {/* Conversation. Bubbles + tool-call style cards. */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {turns.map((t, idx) => {
          if (t.kind === 'fix-prefix') {
            return (
              <Box key={idx} sx={{
                display: 'flex', alignItems: 'flex-start', gap: 1.25,
                p: 1.25, borderRadius: `${c.radius.lg}px`,
                bgcolor: c.status.errorBg,
                border: `1px solid ${c.status.error}30`,
              }}>
                <Box sx={{
                  width: 32, height: 32, borderRadius: `${c.radius.md}px`,
                  bgcolor: c.status.error + '22', color: c.status.error,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <BuildRounded sx={{ fontSize: 16 }} />
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography sx={{ fontSize: '0.92rem', fontWeight: 700, color: c.text.primary, lineHeight: 1.3 }}>
                    Fixing Step {t.stepIdx + 1}: {t.stepLabel}
                  </Typography>
                  <Typography sx={{ fontSize: '0.82rem', color: c.text.secondary, mt: 0.25, lineHeight: 1.45 }}>
                    {t.error}
                  </Typography>
                </Box>
              </Box>
            );
          }
          if (t.kind === 'assistant') {
            return (
              <Box key={idx} sx={{
                p: 1.25, borderRadius: `${c.radius.lg}px`,
                bgcolor: c.bg.surface,
                border: `1px solid ${c.border.subtle}`,
              }}>
                <Typography sx={{ fontSize: '0.92rem', color: c.text.primary, lineHeight: 1.45 }}>
                  {t.text}
                </Typography>
              </Box>
            );
          }
          if (t.kind === 'user') {
            return (
              <Box key={idx} sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Box sx={{
                  px: 1.5, py: 0.85, borderRadius: `${c.radius.lg}px`,
                  bgcolor: c.bg.secondary,
                  maxWidth: '85%',
                }}>
                  <Typography sx={{ fontSize: '0.92rem', color: c.text.primary, lineHeight: 1.45 }}>
                    {t.text}
                  </Typography>
                </Box>
              </Box>
            );
          }
          // proposal
          return (
            <Box key={idx} sx={{
              p: 1.25, borderRadius: `${c.radius.lg}px`,
              bgcolor: c.accent.primary + '10',
              border: `1px solid ${c.accent.primary}30`,
              display: 'flex', flexDirection: 'column', gap: 0.6,
            }}>
              <Typography sx={{ fontSize: '0.82rem', fontWeight: 700, color: c.accent.primary }}>
                Proposed change to Step {t.stepIdx + 1}
              </Typography>
              {t.explanation && (
                <Typography sx={{ fontSize: '0.82rem', color: c.text.secondary, lineHeight: 1.45 }}>
                  {t.explanation}
                </Typography>
              )}
              <Box sx={{
                p: 1, borderRadius: `${c.radius.md}px`,
                bgcolor: c.bg.surface, border: `1px solid ${c.border.subtle}`,
              }}>
                <Typography sx={{ fontSize: '0.78rem', fontWeight: 700, color: c.text.muted, mb: 0.35 }}>AFTER</Typography>
                <Typography sx={{ fontSize: '0.86rem', color: c.text.primary, whiteSpace: 'pre-wrap', lineHeight: 1.45 }}>
                  {t.after}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                {t.applied ? (
                  <Typography sx={{ fontSize: '0.82rem', color: c.status.success, fontWeight: 700 }}>Applied to draft</Typography>
                ) : (
                  <Box
                    onClick={() => onApplyProposal(idx)}
                    role="button"
                    sx={{
                      fontSize: '0.82rem', fontWeight: 700,
                      color: '#fff', bgcolor: c.accent.primary,
                      px: 1.25, py: 0.4, borderRadius: 999, cursor: 'pointer',
                      '&:hover': { filter: 'brightness(1.05)' },
                    }}>
                    Apply to draft
                  </Box>
                )}
              </Box>
            </Box>
          );
        })}
      </Box>
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
          maxRows={5}
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
              display: 'inline-flex', alignItems: 'center', gap: 0.3,
              fontSize: '0.78rem', fontWeight: 700,
              color: '#fff', bgcolor: c.accent.primary,
              px: 1.2, py: 0.4, borderRadius: 999,
              cursor: busy || !draft.trim() ? 'not-allowed' : 'pointer',
              opacity: busy || !draft.trim() ? 0.5 : 1,
              '&:hover': { filter: 'brightness(1.05)' },
            }}>
            <PlayArrowRounded sx={{ fontSize: 14 }} />
            {busy ? 'Working…' : 'Send'}
          </Box>
        </Box>
      </Box>

      <Dialog open={showSaveModal} onClose={() => setShowSaveModal(false)}>
        <Box sx={{ p: 2.5, minWidth: 380, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          <Typography sx={{ fontSize: '1rem', fontWeight: 700, color: c.text.primary }}>
            Save changes to workflow?
          </Typography>
          <Typography sx={{ fontSize: '0.9rem', color: c.text.secondary, lineHeight: 1.5 }}>
            You&apos;re replacing the saved steps with your edits. The next scheduled run will use the new version.
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.4, mt: 0.5 }}>
            {draftSteps.map((s, i) => {
              const changed = (s.text || '') !== (steps[i]?.text || '');
              return (
                <Typography key={s.id} sx={{
                  fontSize: '0.82rem',
                  color: changed ? c.accent.primary : c.text.muted,
                  fontWeight: changed ? 600 : 500,
                }}>
                  {changed ? '●' : '○'} Step {i + 1}: {s.label || (s.text || '').slice(0, 60)}
                </Typography>
              );
            })}
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 0.5 }}>
            <Box onClick={() => setShowSaveModal(false)} role="button" sx={{ fontSize: '0.86rem', color: c.text.secondary, px: 1, py: 0.6, cursor: 'pointer', '&:hover': { color: c.text.primary } }}>
              Keep editing
            </Box>
            <Box
              onClick={onConfirmSave}
              role="button"
              sx={{
                fontSize: '0.86rem', fontWeight: 700, color: '#fff', bgcolor: c.status.success,
                px: 1.4, py: 0.55, borderRadius: 999, cursor: 'pointer',
                '&:hover': { filter: 'brightness(1.05)' },
              }}>
              {busy ? 'Saving…' : 'Save & close'}
            </Box>
          </Box>
        </Box>
      </Dialog>
    </Box>
  );
}

function HeaderBtn({ label, icon, onClick, tone, disabled }: { label: string; icon: React.ReactNode; onClick: () => void; tone: 'muted' | 'filled'; disabled?: boolean }) {
  const c = useClaudeTokens();
  const filled = tone === 'filled';
  return (
    <Box
      onClick={disabled ? undefined : onClick}
      role="button"
      sx={{
        display: 'inline-flex', alignItems: 'center', gap: 0.4,
        fontSize: '0.82rem', fontWeight: 700,
        px: 1.1, py: 0.45, borderRadius: 999,
        color: filled ? '#fff' : c.text.secondary,
        bgcolor: filled ? c.text.primary : 'transparent',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        '&:hover': filled ? { filter: 'brightness(1.05)' } : { color: c.text.primary, bgcolor: c.bg.elevated },
      }}>
      {icon}
      {label}
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
