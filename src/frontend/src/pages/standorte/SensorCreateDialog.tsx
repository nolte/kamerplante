import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Dialog from '@mui/material/Dialog';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Form from '@/components/form/Form';
import FormTextField from '@/components/form/FormTextField';
import FormSelectField from '@/components/form/FormSelectField';
import FormSwitchField from '@/components/form/FormSwitchField';
import FormActions from '@/components/form/FormActions';
import { useNotification } from '@/hooks/useNotification';
import { useApiError } from '@/hooks/useApiError';
import * as tankApi from '@/api/endpoints/tanks';
import * as sitesApi from '@/api/endpoints/sites';
import type { HAEntitySuggestion } from '@/api/endpoints/tanks';
import type { Sensor } from '@/api/types';

export type SensorParentType = 'tank' | 'site' | 'location';

export interface SensorContext {
  parentType: SensorParentType;
  parentKey: string;
}

const metricTypes = ['ph', 'ec_ms', 'water_temp_celsius', 'fill_level_percent', 'tds_ppm', 'dissolved_oxygen_mgl', 'orp_mv', 'temperature_celsius', 'humidity_percent', 'co2_ppm', 'vpd_kpa', 'ppfd'] as const;

const schema = z.object({
  name: z.string().min(1).max(200),
  metric_type: z.string().min(1),
  ha_entity_id: z.string().nullable(),
  unit_of_measurement: z.string().nullable(),
  mqtt_topic: z.string().nullable(),
  is_active: z.boolean(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onClose: () => void;
  context: SensorContext;
  sensor?: Sensor;
  onSaved: () => void;
}

export default function SensorCreateDialog({ open, onClose, context, sensor, onSaved }: Props) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const { t } = useTranslation();
  const notification = useNotification();
  const { handleError } = useApiError();
  const [saving, setSaving] = useState(false);
  const [haEntities, setHaEntities] = useState<HAEntitySuggestion[]>([]);
  const [loadingEntities, setLoadingEntities] = useState(false);
  const isEdit = !!sensor;

  const { control, handleSubmit, reset, setValue } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      metric_type: 'ec_ms',
      ha_entity_id: null,
      unit_of_measurement: null,
      mqtt_topic: null,
      is_active: true,
    },
  });

  useEffect(() => {
    if (open) {
      if (sensor) {
        reset({
          name: sensor.name,
          metric_type: sensor.metric_type,
          ha_entity_id: sensor.ha_entity_id,
          unit_of_measurement: sensor.unit_of_measurement ?? null,
          mqtt_topic: sensor.mqtt_topic,
          is_active: sensor.is_active,
        });
      } else {
        reset({
          name: '',
          metric_type: context.parentType === 'tank' ? 'ec_ms' : 'temperature_celsius',
          ha_entity_id: null,
          unit_of_measurement: null,
          mqtt_topic: null,
          is_active: true,
        });
      }
      // Load HA entities
      setLoadingEntities(true);
      tankApi.listHaEntities()
        .then(setHaEntities)
        .catch(() => setHaEntities([]))
        .finally(() => setLoadingEntities(false));
    }
  }, [open, sensor, reset, context.parentType]);

  const handleEntitySelect = (_event: unknown, entity: HAEntitySuggestion | null) => {
    if (!entity) return;
    setValue('ha_entity_id', entity.entity_id);
    setValue('unit_of_measurement', entity.unit_of_measurement ?? null);
    if (entity.suggested_name) {
      setValue('name', entity.suggested_name);
    }
    if (entity.suggested_metric_type) {
      setValue('metric_type', entity.suggested_metric_type);
    }
  };

  const onSubmit = async (data: FormData) => {
    try {
      setSaving(true);
      if (isEdit) {
        const changes = {
          name: data.name,
          metric_type: data.metric_type,
          ha_entity_id: data.ha_entity_id || null,
          unit_of_measurement: data.unit_of_measurement || null,
          mqtt_topic: data.mqtt_topic || null,
          is_active: data.is_active,
        };
        // Scoped by the parent, exactly like the create branch below: a sensor
        // carries no tenant of its own, so the backend verifies the tank / site
        // / location it hangs off and refuses a sensor that hangs off another
        // one (#1339).
        switch (context.parentType) {
          case 'tank':
            await tankApi.updateSensor(context.parentKey, sensor.key, changes);
            break;
          case 'site':
            await sitesApi.updateSiteSensor(context.parentKey, sensor.key, changes);
            break;
          case 'location':
            await sitesApi.updateLocationSensor(context.parentKey, sensor.key, changes);
            break;
        }
        notification.success(t('common.saved'));
      } else {
        const payload = {
          name: data.name,
          metric_type: data.metric_type,
          ha_entity_id: data.ha_entity_id || null,
          unit_of_measurement: data.unit_of_measurement || null,
          mqtt_topic: data.mqtt_topic || null,
        };
        switch (context.parentType) {
          case 'tank':
            await tankApi.createSensor(context.parentKey, { ...payload, tank_key: context.parentKey });
            break;
          case 'site':
            await sitesApi.createSiteSensor(context.parentKey, payload);
            break;
          case 'location':
            await sitesApi.createLocationSensor(context.parentKey, payload);
            break;
        }
        notification.success(t('pages.sensors.created'));
      }
      onSaved();
    } catch (err) {
      handleError(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog fullScreen={fullScreen} open={open} onClose={onClose} maxWidth="sm" fullWidth aria-labelledby="sensor-create-dialog-title" data-testid="sensor-create-dialog">
      <DialogTitle id="sensor-create-dialog-title">{isEdit ? t('pages.sensors.edit') : t('pages.sensors.add')}</DialogTitle>
      <DialogContent>
        <Form onSubmit={handleSubmit(onSubmit)}>
          {haEntities.length > 0 && (
            <Autocomplete
              options={haEntities}
              loading={loadingEntities}
              getOptionLabel={(o) => `${o.friendly_name} (${o.entity_id})`}
              renderOption={(props, option) => (
                <li {...props} key={option.entity_id}>
                  <Box>
                    <Typography variant="body2">{option.friendly_name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {option.entity_id}
                      {option.state != null && ` — ${option.state}`}
                      {option.unit_of_measurement && ` ${option.unit_of_measurement}`}
                    </Typography>
                    {option.suggested_metric_type && (
                      <Chip label={option.suggested_metric_type} size="small" sx={{ ml: 1 }} />
                    )}
                  </Box>
                </li>
              )}
              onChange={handleEntitySelect}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label={t('pages.sensors.haEntitySelect')}
                  helperText={t('pages.sensors.haEntitySelectHelper')}
                  margin="normal"
                  fullWidth
                />
              )}
              sx={{ mb: 1 }}
            />
          )}
          <FormTextField
            name="name"
            control={control}
            label={t('pages.sensors.name')}
            required
          />
          <FormSelectField
            name="metric_type"
            control={control}
            label={t('pages.sensors.metricType')}
            helperText={t('pages.sensors.metricTypeHelper')}
            options={metricTypes.map((v) => ({
              value: v,
              label: t(`enums.sensorMetricType.${v}`, { defaultValue: v }),
            }))}
          />
          {haEntities.length === 0 && (
            <FormTextField
              name="ha_entity_id"
              control={control}
              label={t('pages.sensors.haEntityId')}
              helperText={t('pages.sensors.haEntityIdHelper')}
            />
          )}
          <FormTextField
            name="mqtt_topic"
            control={control}
            label={t('pages.sensors.mqttTopic')}
          />
          {isEdit && (
            <FormSwitchField
              name="is_active"
              control={control}
              label={t('pages.sensors.active')}
            />
          )}
          <FormActions
            onCancel={onClose}
            loading={saving}
            saveLabel={isEdit ? t('common.save') : t('common.create')}
          />
        </Form>
      </DialogContent>
    </Dialog>
  );
}
