import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Skeleton from '@mui/material/Skeleton';
import RefreshIcon from '@mui/icons-material/Refresh';
import AIResponse from './AIResponse';
import { useExpertiseLevel } from '@/hooks/useExpertiseLevel';
import { useTenantPermissions } from '@/hooks/useTenantPermissions';
import { aiApi } from '@/api';
import type { AiTipCard } from '@/api/types';

export interface TipCardsPanelProps {
  /** Context type: `plant_instance` | `planting_run` | `general`. */
  contextType: string;
  /** Context key (plant/run key). */
  contextKey: string;
  /** Optional heading above the cards. */
  title?: string;
}

/**
 * REQ-031 §6.2 — Tipp-Karten fuer einen Pflanzen-/Run-Kontext.
 *
 * Jede Karte wird durch die `<AIResponse>`-Huelle gerendert. Beginner sehen
 * kompaktere Karten (max 2) mit zugeklapptem Quellen-Footer (REQ-021). Ein
 * "Aktualisieren"-Button erzwingt eine Neugenerierung. Die Sichtbarkeit ist an
 * Stufe-2 (Tenant-Setting) gebunden — der aufrufende Kontext blendet das Panel
 * aus, wenn KI fuer den Tenant deaktiviert ist.
 */
export default function TipCardsPanel({ contextType, contextKey, title }: TipCardsPanelProps) {
  const { t, i18n } = useTranslation();
  const { level } = useExpertiseLevel();
  const [tips, setTips] = useState<AiTipCard[] | null>(null);
  const [loading, setLoading] = useState(false);

  const language = i18n.language.startsWith('en') ? 'en' : 'de';

  const load = useCallback(
    async (force: boolean) => {
      setLoading(true);
      try {
        const result = force
          ? await aiApi.refreshTips(contextType, contextKey, language)
          : await aiApi.getTips(contextType, contextKey, language);
        setTips(result);
      } catch {
        // Online-only feature (UI-NFR-012): hide the panel when it has nothing to
        // show. A *forced* refresh that fails is different — the panel already
        // holds tips the reader may see, and clearing them turns a failed
        // regeneration into the loss of the read surface too. #1353 made that
        // reachable: `POST /ai/tips/refresh` answers 403 to a viewer, and before
        // this the whole panel vanished on the click.
        if (!force) setTips([]);
      } finally {
        setLoading(false);
      }
    },
    [contextType, contextKey, language],
  );

  useEffect(() => {
    void load(false);
  }, [load]);

  // Regenerating tips is a write on the server (`require_tenant_role(grower)`
  // since #1353); `canEdit` is the same predicate, so the control is absent for a
  // viewer rather than present and refused.
  const { canEdit } = useTenantPermissions();

  const maxCards = level === 'beginner' ? 2 : 4;
  const visibleTips = (tips ?? []).slice(0, maxCards);

  if (loading && tips === null) {
    return (
      <Box data-testid="tip-cards-loading">
        <Skeleton variant="rounded" height={90} sx={{ mb: 1 }} />
        <Skeleton variant="rounded" height={90} />
      </Box>
    );
  }

  if (tips !== null && visibleTips.length === 0) {
    return null;
  }

  return (
    <Box data-testid="tip-cards-panel">
      <Stack
        direction="row"
        sx={{ mb: 1, alignItems: 'center', justifyContent: 'space-between' }}
      >
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          {title ?? t('ai.tips.heading')}
        </Typography>
        {canEdit && (
        <Button
          size="small"
          startIcon={<RefreshIcon />}
          onClick={() => void load(true)}
          disabled={loading}
          sx={{ minHeight: 48 }}
          data-testid="tip-cards-refresh"
        >
          {t('ai.tips.refresh')}
        </Button>
        )}
      </Stack>

      <Stack spacing={1.5}>
        {visibleTips.map((tip) => (
          <Card key={tip.key ?? tip.title} variant="outlined">
            <CardContent>
              <AIResponse
                sources={tip.sources}
                modelName={tip.model_name}
                usesTenantData={tip.uses_tenant_data}
                confidence={tip.confidence}
                languageMismatchWarning={tip.language_mismatch_warning}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  {tip.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {tip.body}
                </Typography>
              </AIResponse>
            </CardContent>
            {tip.action_url && (
              <CardActions>
                <Button size="small" href={tip.action_url}>
                  {t('ai.tips.learnMore')}
                </Button>
              </CardActions>
            )}
          </Card>
        ))}
      </Stack>
    </Box>
  );
}
