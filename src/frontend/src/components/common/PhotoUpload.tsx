import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import IconButton from '@mui/material/IconButton';
import AddAPhotoIcon from '@mui/icons-material/AddAPhoto';
import DeleteIcon from '@mui/icons-material/Delete';
import { useNotification } from '@/hooks/useNotification';
import { useApiError } from '@/hooks/useApiError';
import AuthImage from '@/components/common/AuthImage';
import * as taskApi from '@/api/endpoints/tasks';

interface Props {
  taskKey: string;
  photoRefs: string[];
  onChange: (refs: string[]) => void;
  disabled?: boolean;
}

export default function PhotoUpload({ taskKey, photoRefs, onChange, disabled }: Props) {
  const { t } = useTranslation();
  const notification = useNotification();
  const { handleError } = useApiError();
  const [uploading, setUploading] = useState(false);

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;

      setUploading(true);
      const newRefs = [...photoRefs];
      try {
        for (const file of Array.from(files)) {
          const result = await taskApi.uploadTaskPhoto(taskKey, file);
          newRefs.push(result.uri);
        }
        onChange(newRefs);
        notification.success(t('pages.tasks.photoUploaded'));
      } catch (err) {
        handleError(err);
      } finally {
        setUploading(false);
        e.target.value = '';
      }
    },
    [taskKey, photoRefs, onChange, notification, handleError, t],
  );

  const handleRemove = useCallback(
    (index: number) => {
      const updated = photoRefs.filter((_, i) => i !== index);
      onChange(updated);
    },
    [photoRefs, onChange],
  );

  return (
    <Box data-testid="photo-upload">
      <Button
        component="label"
        variant="outlined"
        startIcon={uploading ? <CircularProgress size={16} /> : <AddAPhotoIcon />}
        disabled={disabled || uploading}
        sx={{ mb: 1 }}
      >
        {uploading ? t('pages.tasks.photoUploading') : t('pages.tasks.photoUpload')}
        <input
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={handleFileChange}
        />
      </Button>

      {photoRefs.length > 0 && (
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
          {photoRefs.map((ref, i) => (
            <Box
              key={ref}
              sx={{
                position: 'relative',
                width: 80,
                height: 80,
                borderRadius: 1,
                overflow: 'hidden',
                border: '1px solid',
                borderColor: 'divider',
              }}
            >
              <AuthImage
                uri={ref}
                alt={t('pages.tasks.photoAlt', { index: i + 1 })}
                data-testid={`photo-preview-${i}`}
              />
              <IconButton
                size="small"
                onClick={() => handleRemove(i)}
                disabled={disabled}
                aria-label={t('pages.tasks.photoRemove', { index: i + 1 })}
                data-testid={`photo-remove-${i}`}
                sx={{
                  position: 'absolute',
                  top: 0,
                  right: 0,
                  bgcolor: 'background.paper',
                  '&:hover': { bgcolor: 'error.light', color: 'error.contrastText' },
                }}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>
          ))}
        </Box>
      )}

      {photoRefs.length === 0 && (
        <Typography variant="caption" color="text.secondary">
          {t('pages.tasks.noPhotos')}
        </Typography>
      )}
    </Box>
  );
}
