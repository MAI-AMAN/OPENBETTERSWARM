// Windows-aware shim for framer-motion. On Mac, re-exports the real library; on Windows, motion.* becomes a plain HTML element (no animation, no Framer runtime, no segfault). AnimatePresence passes children through. Onboarding files import from here so a single Mac/Windows fork lives in one place.

import React from 'react';
import * as fm from 'framer-motion';

const IS_WIN = typeof navigator !== 'undefined' && navigator.userAgent.includes('Windows');

const FRAMER_ONLY_PROPS = new Set([
  'initial', 'animate', 'exit', 'transition', 'variants', 'layoutId', 'layout',
  'drag', 'dragConstraints', 'dragElastic', 'dragMomentum', 'dragControls',
  'dragDirectionLock', 'dragListener', 'dragTransition', 'dragSnapToOrigin', 'dragPropagation',
  'onDragStart', 'onDragEnd', 'onDrag', 'onDirectionLock',
  'onAnimationStart', 'onAnimationComplete', 'onUpdate',
  'onLayoutAnimationStart', 'onLayoutAnimationComplete',
  'whileHover', 'whileTap', 'whileFocus', 'whileDrag', 'whileInView',
  'viewport', 'transformTemplate', 'custom', 'inherit',
]);

const stripFramerProps = (props: any) => {
  const out: any = {};
  for (const k in props) {
    if (!FRAMER_ONLY_PROPS.has(k)) out[k] = props[k];
  }
  return out;
};

const motionShim: any = new Proxy({}, {
  get: (_target, tag: string) => {
    return React.forwardRef((props: any, ref: any) =>
      React.createElement(tag, { ...stripFramerProps(props), ref })
    );
  },
});

export const motion: typeof fm.motion = IS_WIN ? motionShim : fm.motion;
export const AnimatePresence: typeof fm.AnimatePresence = IS_WIN
  ? (({ children }: any) => children) as any
  : fm.AnimatePresence;

const animationControlsStub = {
  start: () => Promise.resolve(),
  stop: () => {},
  set: () => {},
  mount: () => () => {},
};
export const useAnimationControls: typeof fm.useAnimationControls = IS_WIN
  ? (() => animationControlsStub as any) as any
  : fm.useAnimationControls;
