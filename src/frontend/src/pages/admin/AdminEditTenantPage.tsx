import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import Typography from '@mui/material/Typography';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Autocomplete from '@mui/material/Autocomplete';
import DeleteIcon from '@mui/icons-material/Delete';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import PageTitle from '@/components/layout/PageTitle';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';
import { useSnackbar } from 'notistack';
import {
  fetchAdminTenants,
  fetchAdminUsers,
  updateAdminTenant,
  deleteAdminTenant,
  fetchTenantMembers,
  addTenantMember,
  removeTenantMember,
  changeTenantMemberRole,
} from '@/api/endpoints/adminPlatform';
import { isApiError, parseApiError } from '@/api/errors';
import ErrorPage from '@/pages/ErrorPage';
import type { AdminTenant, AdminTenantMember, AdminUser, TenantRole } from '@/api/types';

const GRID_2COL = {
  display: 'grid',
  gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' },
  gap: 3,
} as const;

export default function AdminEditTenantPage() {
  const { key } = useParams<{ key: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();

  const [tenant, setTenant] = useState<AdminTenant | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<number | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  // Form
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Members
  const [members, setMembers] = useState<AdminTenantMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [allUsers, setAllUsers] = useState<AdminUser[]>([]);
  const [showAddMember, setShowAddMember] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [selectedRole, setSelectedRole] = useState<TenantRole>('viewer');
  const [adding, setAdding] = useState(false);

  const isPlatform = tenant?.is_platform === true;

  // Load tenant
  useEffect(() => {
    if (!key) return;
    setLoading(true);
    setLoadError(null);
    // A per-run flag, because the effect re-runs on `key` and on retry. Before
    // the `.catch` existed a late rejection from a superseded request was merely
    // unhandled; now it would call `setLoadError` and swap a healthy, fully
    // loaded page for an error state belonging to a record the operator has
    // already navigated away from. Same pattern as `useSiteWeatherForecast`.
    let cancelled = false;
    fetchAdminTenants()
      .then((tenants) => {
        if (cancelled) return;
        const found = tenants.find((t) => t.key === key);
        if (found) {
          setTenant(found);
          setName(found.name);
          setDescription(found.description ?? '');
          setIsActive(found.is_active);
        }
      })
      // WITHOUT THIS `.catch` EVERY REJECTION LOOKED LIKE "NOT FOUND" (#1390).
      // A 403, a 500, a dropped connection and a rate limit all left `tenant` at
      // `null`, and the render below falls through to the not-found alert — so an
      // operator was told a record does not exist while it sits there untouched.
      // The rejection was also unhandled, surfacing as an unhandled promise
      // rejection rather than anywhere a user or an operator could see it.
      //
      // `<RequirePlatformAdmin>` (#1336) removed the 403-for-a-non-admin case by
      // not mounting the page at all for those callers. It does not touch the
      // rest: a platform admin who hits a 500 or loses the network still read
      // "not found" until this.
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(isApiError(err) ? err.statusCode : 0);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [key, reloadToken]);

  // Load members
  const loadMembers = useCallback(async () => {
    if (!key) return;
    setMembersLoading(true);
    try {
      setMembers(await fetchTenantMembers(key));
    } catch { /* ignore */ }
    finally { setMembersLoading(false); }
  }, [key]);

  useEffect(() => { loadMembers(); }, [loadMembers]);

  // Lazy-load all users when add-member opens
  useEffect(() => {
    if (showAddMember && allUsers.length === 0) {
      fetchAdminUsers().then(setAllUsers).catch(() => {});
    }
  }, [showAddMember, allUsers.length]);

  const availableUsers = allUsers.filter(
    (u) => u.is_active && !members.some((m) => m.user_key === u.key),
  );

  const handleSave = async () => {
    if (!tenant || isPlatform) return;
    setSaving(true);
    try {
      const updated = await updateAdminTenant(tenant.key, {
        name: name !== tenant.name ? name : undefined,
        description: description !== (tenant.description ?? '') ? description : undefined,
        is_active: isActive !== tenant.is_active ? isActive : undefined,
      });
      setTenant(updated);
      enqueueSnackbar(t('common.saved'), { variant: 'success' });
    } catch (err) {
      enqueueSnackbar(parseApiError(err), { variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!tenant || isPlatform) return;
    setDeleting(true);
    try {
      await deleteAdminTenant(tenant.key);
      enqueueSnackbar(t('pages.auth.adminTenantDeleted'), { variant: 'success' });
      navigate('/settings#platform');
    } catch (err) {
      enqueueSnackbar(parseApiError(err), { variant: 'error' });
    } finally {
      setDeleting(false);
    }
  };

  const handleAddMember = async () => {
    if (!key || !selectedUser) return;
    setAdding(true);
    try {
      const m = await addTenantMember(key, { user_key: selectedUser.key, role: selectedRole });
      setMembers((prev) => [...prev, m]);
      setSelectedUser(null);
      setSelectedRole('viewer');
      setShowAddMember(false);
      enqueueSnackbar(t('pages.auth.adminMemberAdded'), { variant: 'success' });
    } catch (err) {
      enqueueSnackbar(parseApiError(err), { variant: 'error' });
    } finally {
      setAdding(false);
    }
  };

  const handleRemoveMember = async (m: AdminTenantMember) => {
    if (!key) return;
    try {
      await removeTenantMember(key, m.membership_key);
      setMembers((prev) => prev.filter((x) => x.membership_key !== m.membership_key));
      enqueueSnackbar(t('pages.auth.adminMemberRemoved'), { variant: 'success' });
    } catch (err) {
      enqueueSnackbar(parseApiError(err), { variant: 'error' });
    }
  };

  const handleRoleChange = async (m: AdminTenantMember, newRole: TenantRole) => {
    if (!key) return;
    try {
      const updated = await changeTenantMemberRole(key, m.membership_key, newRole);
      setMembers((prev) => prev.map((x) => (x.membership_key === m.membership_key ? updated : x)));
      enqueueSnackbar(t('common.saved'), { variant: 'success' });
    } catch (err) {
      enqueueSnackbar(parseApiError(err), { variant: 'error' });
    }
  };

  if (loading) return <LoadingSkeleton variant="form" />;
  // THREE ANSWERS, NOT ONE (#1390). A failed request is not a missing record, and
  // only the third of these is genuinely "not found": the list came back and the
  // key was not in it.
  if (loadError !== null) {
    // `0` means the failure carried no status at all — a dropped connection, DNS,
    // a blocked request. Rendering that as 500 tells an offline operator the
    // server failed, which is a different and wrong diagnosis. 503 is the closest
    // honest answer: the service could not be reached.
    return (
      <ErrorPage
        statusCode={loadError === 0 ? 503 : loadError}
        onRetry={() => setReloadToken((n) => n + 1)}
        landmark={false}
      />
    );
  }
  if (!tenant) return <Alert severity="error">{t('pages.admin.tenantNotFound')}</Alert>;

  return (
    <Box sx={{ mt: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <IconButton onClick={() => navigate('/settings#platform')} data-testid="back-btn">
          <ArrowBackIcon />
        </IconButton>
        <PageTitle title={`${t('pages.auth.editTenantTitle')}: ${tenant.name}`} />
        {isPlatform && <Chip label="Platform" color="warning" size="small" />}
        <Chip
          label={tenant.is_active ? t('pages.auth.adminStatusActive') : t('pages.auth.adminStatusInactive')}
          color={tenant.is_active ? 'success' : 'default'}
          size="small"
        />
      </Box>

      <Box sx={GRID_2COL}>
        {/* Left: Tenant properties */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              {t('pages.auth.adminTenantName')}
            </Typography>
            {isPlatform && (
              <Alert severity="info" sx={{ mb: 2 }}>{t('pages.auth.editTenantReadonly')}</Alert>
            )}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              <TextField
                label={t('pages.auth.adminTenantName')}
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isPlatform}
                fullWidth
                required
                data-testid="edit-tenant-name"
              />
              <TextField
                label={t('pages.auth.adminTenantDescription')}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isPlatform}
                fullWidth
                multiline
                minRows={3}
                data-testid="edit-tenant-description"
              />
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <TextField label="Slug" value={tenant.slug} disabled sx={{ flex: 1 }} />
                <TextField label={t('pages.auth.adminTenantType')} value={t(`enums.tenantType.${tenant.tenant_type}`)} disabled sx={{ flex: 1 }} />
              </Box>
              <FormControlLabel
                control={
                  <Switch checked={isActive} onChange={(e) => setIsActive(e.target.checked)} disabled={isPlatform} data-testid="edit-tenant-active-switch" />
                }
                label={t('pages.auth.adminUserIsActive')}
              />
              {!isPlatform && (
                <Button
                  variant="contained"
                  onClick={handleSave}
                  disabled={saving || !name.trim()}
                  startIcon={saving ? <CircularProgress size={16} /> : undefined}
                  sx={{ alignSelf: 'flex-start' }}
                  data-testid="edit-tenant-save"
                >
                  {t('common.save')}
                </Button>
              )}
            </Box>

            {/* Danger zone */}
            {!isPlatform && (
              <>
                <Divider sx={{ my: 3 }} />
                <Typography variant="subtitle2" color="error" gutterBottom>
                  {t('pages.auth.dangerZone')}
                </Typography>
                {!confirmDelete ? (
                  <Button variant="outlined" color="error" onClick={() => setConfirmDelete(true)} data-testid="delete-tenant-btn">
                    {t('pages.auth.adminDeleteTenant')}
                  </Button>
                ) : (
                  <Alert severity="error">
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      {t('pages.auth.adminDeleteTenantConfirm', { name: tenant.name })}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button variant="contained" color="error" size="small" onClick={handleDelete} disabled={deleting}
                        startIcon={deleting ? <CircularProgress size={14} /> : undefined} data-testid="confirm-delete-tenant-btn">
                        {t('pages.auth.adminConfirmDelete')}
                      </Button>
                      <Button size="small" onClick={() => setConfirmDelete(false)}>{t('common.cancel')}</Button>
                    </Box>
                  </Alert>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Right: Members */}
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6">
                {t('pages.auth.adminTenantMembersTitle')} <Chip label={members.length} size="small" />
              </Typography>
              {!showAddMember && (
                <Button size="small" startIcon={<PersonAddIcon />} onClick={() => setShowAddMember(true)} data-testid="show-add-member-btn">
                  {t('pages.auth.adminAddMember')}
                </Button>
              )}
            </Box>

            {/* Add member */}
            {showAddMember && (
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start', p: 2, mb: 2, border: 1, borderColor: 'divider', borderRadius: 1, flexWrap: 'wrap' }}>
                <Autocomplete
                  size="small"
                  options={availableUsers}
                  getOptionLabel={(u) => `${u.display_name} (${u.email})`}
                  value={selectedUser}
                  onChange={(_, v) => setSelectedUser(v)}
                  renderInput={(params) => <TextField {...params} label={t('pages.auth.adminSelectUser')} data-testid="add-member-user-input" />}
                  sx={{ flex: 1, minWidth: 220 }}
                />
                <FormControl size="small" sx={{ minWidth: 140 }}>
                  <InputLabel>{t('pages.auth.adminMemberRole')}</InputLabel>
                  <Select value={selectedRole} label={t('pages.auth.adminMemberRole')} onChange={(e) => setSelectedRole(e.target.value as TenantRole)}>
                    <MenuItem value="lead">{t('enums.tenantRole.lead')}</MenuItem>
                    <MenuItem value="grower">{t('enums.tenantRole.grower')}</MenuItem>
                    <MenuItem value="viewer">{t('enums.tenantRole.viewer')}</MenuItem>
                  </Select>
                </FormControl>
                <Button variant="contained" size="small" onClick={handleAddMember} disabled={adding || !selectedUser}
                  startIcon={adding ? <CircularProgress size={14} /> : undefined} sx={{ mt: 0.25 }} data-testid="add-member-submit-btn">
                  {t('common.add')}
                </Button>
                <Button size="small" onClick={() => { setShowAddMember(false); setSelectedUser(null); }} sx={{ mt: 0.25 }}>
                  {t('common.cancel')}
                </Button>
              </Box>
            )}

            {/* Members table */}
            {membersLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}><CircularProgress /></Box>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('pages.auth.adminUserName')}</TableCell>
                      <TableCell>{t('pages.auth.adminUserEmail')}</TableCell>
                      <TableCell>{t('pages.auth.adminMemberRole')}</TableCell>
                      <TableCell align="right" />
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {members.map((m) => (
                      <TableRow key={m.membership_key}>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>{m.display_name}</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>{m.email}</Typography>
                        </TableCell>
                        <TableCell>
                          <Select
                            size="small"
                            value={m.role}
                            onChange={(e) => handleRoleChange(m, e.target.value as TenantRole)}
                            variant="standard"
                            sx={{ fontSize: '0.8125rem' }}
                            data-testid={`role-select-${m.user_key}`}
                          >
                            <MenuItem value="lead">{t('enums.tenantRole.lead')}</MenuItem>
                            <MenuItem value="grower">{t('enums.tenantRole.grower')}</MenuItem>
                            <MenuItem value="viewer">{t('enums.tenantRole.viewer')}</MenuItem>
                          </Select>
                        </TableCell>
                        <TableCell align="right">
                          <IconButton size="small" onClick={() => handleRemoveMember(m)} data-testid={`remove-member-${m.user_key}`}>
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                    {members.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={4} align="center">
                          <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                            {t('pages.auth.adminNoMemberships')}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
