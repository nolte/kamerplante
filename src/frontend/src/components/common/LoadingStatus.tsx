import Box from '@mui/material/Box';
import { visuallyHidden } from '@mui/utils';
import { useTranslation } from 'react-i18next';

interface LoadingStatusProps {
  /** Overrides the generic "loading" wording where a region-specific one exists. */
  label?: string;
  /**
   * Whether the region currently has something to say. `false` keeps the node
   * mounted but empties and un-names it — see property 4 below. Defaults to
   * `true`, which is the "mounted only while loading" usage of every existing
   * call site.
   */
  active?: boolean;
  'data-testid'?: string;
}

/**
 * The announcement half of a loading placeholder (UI-NFR-002, issue #1324).
 *
 * The pattern this replaces was `<div aria-busy="true" aria-label="Loading …">`,
 * repeated at ten sites. A `<div>` maps to `generic`, ARIA prohibits naming a
 * generic element, and the name is therefore **dropped** — a screen-reader user
 * got no announcement at all, which is the entire purpose of the element. axe
 * reports it as `aria-prohibited-attr` (serious), but only while the skeleton
 * stands, so a scan that waits for the page to settle never sees it.
 *
 * Three things about this shape were measured in Chrome's accessibility tree
 * rather than assumed, and each of them would be easy to "simplify" away:
 *
 * 1. **`role="status"` lives here, not on the busy wrapper.** `aria-busy="true"`
 *    tells assistive technology it may defer presenting a live region until the
 *    updates finish — and this placeholder is removed rather than un-busied, so
 *    "later" never comes. Measured: an element carrying both reports
 *    `busy=1` on the live region itself, while a status node *inside* an
 *    `aria-busy` ancestor reports no busy at all (Chrome does not propagate it).
 *    Putting the role on the wrapper would therefore have shipped a live region
 *    that AT is explicitly invited to stay silent about. The wrapper keeps
 *    `aria-busy` — it is the region in flux — and this node does the announcing.
 *
 * 2. **The text content is what gets announced.** A live region announces its
 *    *content*, not its name, so a `role="status"` with only decorative
 *    `<Skeleton>` children inside has nothing to say. Hence real, visually
 *    hidden text.
 *
 * 3. **`aria-label` as well, and it is not redundant.** `status` takes its name
 *    from the author only, never from content: measured, a `role="status"` whose
 *    only child is this text has an accessible name of `""`. The label is what
 *    gives the region a name for a user who navigates onto it; the content is
 *    what makes it announce. Removing either one silently loses half the fix.
 *
 * 4. **`active={false}` empties the region instead of unmounting it** (#1337).
 *    Most callers render this node only while their placeholder stands, which is
 *    fine when the placeholder is *replaced* by content — the insertion and the
 *    content arrive together and nothing needs to be re-announced. A caller that
 *    loads repeatedly (the dashboard refetches its aggregate on every layout
 *    change) needs the opposite: a live region has to exist *before* its content
 *    changes for the change to be announced, so it stays mounted and goes empty.
 *    Empty **and unnamed** — `status` takes its name from the author, and a name
 *    left in place would describe a load that is over to anyone who navigates
 *    onto the region.
 *
 * Matches the live-region convention already used in `ConfirmDialog`,
 * `RecognitionStatusCard` and `LocationAssignmentSection`.
 */
export default function LoadingStatus({
  label,
  active = true,
  'data-testid': testId,
}: LoadingStatusProps) {
  const { t } = useTranslation();
  const message = label ?? t('common.loading');
  return (
    <Box
      component="span"
      role="status"
      aria-live="polite"
      aria-label={active ? message : undefined}
      sx={visuallyHidden}
      data-testid={testId}
    >
      {active ? message : ''}
    </Box>
  );
}
