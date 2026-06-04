// Run: node --test frontend/src/shared/browserSettle.test.ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { shouldStopWaiting, SETTLE_FLOOR_MS, SETTLE_QUIET_MS } from './browserSettle.ts';

test('does not settle before the floor, even when fully quiet', () => {
  assert.equal(shouldStopWaiting(true, 5000, SETTLE_FLOOR_MS - 1), false);
});

test('settles once past the floor with a complete doc and a long-quiet network', () => {
  assert.equal(shouldStopWaiting(true, SETTLE_QUIET_MS, SETTLE_FLOOR_MS), true);
  assert.equal(shouldStopWaiting(true, 2000, 1000), true);
});

test('does not settle while the document is still loading', () => {
  assert.equal(shouldStopWaiting(false, 5000, 1000), false);
});

test('does not settle when the network was quiet for less than the window', () => {
  assert.equal(shouldStopWaiting(true, SETTLE_QUIET_MS - 1, 1000), false);
});

test('a page that keeps fetching (quiet=0) rides to the cap', () => {
  assert.equal(shouldStopWaiting(true, 0, 9000), false);
});

test('missing/NaN quiet is treated as not-quiet, not as settled', () => {
  assert.equal(shouldStopWaiting(true, undefined as unknown as number, 1000), false);
});
