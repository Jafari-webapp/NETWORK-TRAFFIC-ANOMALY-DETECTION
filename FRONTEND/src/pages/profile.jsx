import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Building2, Shield, Activity, Pencil, Check, X, KeyRound } from 'lucide-react';
import Layout from '../components/Layout';
import * as api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { formatDateTime } from '../utils/datetime';

function SectionCard({ icon: Icon, title, children }) {
  return (
    <div className="p-5 rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-4 h-4 text-slate-400" />
        <p className="text-sm font-bold text-slate-700">{title}</p>
      </div>
      {children}
    </div>
  );
}

function Field({ label, value }) {
  return (
    <div className="py-2 border-b border-slate-100 last:border-0">
      <span className="text-xs text-slate-400">{label}</span>
      <p className="text-sm text-slate-700 font-medium">{value || '—'}</p>
    </div>
  );
}

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();

  // --- Account information edit (Full Name, Username / Email) ---
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  const startEdit = () => {
    setForm({ 
      full_name: user?.full_name || '', 
      username: user?.username || '', 
      email: user?.email || '' 
    });
    setSaveError('');
    setEditing(true);
  };

  const saveProfile = async () => {
    setSaving(true);
    setSaveError('');
    try {
      await api.updateProfile(form);
      await refreshUser();
      setEditing(false);
    } catch (err) {
      setSaveError(api.getErrorMessage(err, 'Could not save changes.'));
    } finally {
      setSaving(false);
    }
  };

  // --- Role & Organization edit ---
  const [editingRoleOrg, setEditingRoleOrg] = useState(false);
  const [roleOrgForm, setRoleOrgForm] = useState(null);
  const [roleOrgSaving, setRoleOrgSaving] = useState(false);
  const [roleOrgError, setRoleOrgError] = useState('');

  const startEditRoleOrg = () => {
    setRoleOrgForm({
      department: user?.department || '',
      organization: user?.organization || '',
    });
    setRoleOrgError('');
    setEditingRoleOrg(true);
  };

  const saveRoleOrg = async () => {
    setRoleOrgSaving(true);
    setRoleOrgError('');
    try {
      await api.updateProfile(roleOrgForm);
      await refreshUser();
      setEditingRoleOrg(false);
    } catch (err) {
      setRoleOrgError(api.getErrorMessage(err, 'Could not save changes.'));
    } finally {
      setRoleOrgSaving(false);
    }
  };

  // --- Change password ---
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [pwSaving, setPwSaving] = useState(false);
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState(false);

  const submitPasswordChange = async (e) => {
    e.preventDefault();
    setPwError('');
    setPwSuccess(false);
    if (pwForm.new_password.length < 8) {
      setPwError('New password must be at least 8 characters.');
      return;
    }
    if (pwForm.new_password !== pwForm.confirm) {
      setPwError('New password and confirmation do not match.');
      return;
    }
    setPwSaving(true);
    try {
      await api.changePassword({
        current_password: pwForm.current_password,
        new_password: pwForm.new_password,
      });
      setPwSuccess(true);
      setPwForm({ current_password: '', new_password: '', confirm: '' });
    } catch (err) {
      setPwError(api.getErrorMessage(err, 'Could not change password.'));
    } finally {
      setPwSaving(false);
    }
  };

  if (!user) return null;

  return (
    <Layout title="Profile">
      <div className="max-w-2xl">
        <div className="mb-5">
          <p className="text-sm text-slate-500">Manage your account and security settings</p>
        </div>

        <div className="space-y-5">
          {/* 1. Account Information */}
          <SectionCard icon={User} title="Account Information">
            {!editing ? (
              <>
                <Field label="Full Name" value={user.full_name} />
                <Field label="Username" value={user.username} />
                <Field label="Email" value={user.email} />
                <button
                  onClick={startEdit}
                  className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-sky-600 hover:text-sky-700"
                >
                  <Pencil className="w-3.5 h-3.5" /> Edit
                </button>
              </>
            ) : (
              <div className="space-y-3">
                {saveError && <p className="text-xs text-rose-600">{saveError}</p>}
                <label className="block text-sm">
                  <span className="text-slate-500 text-xs">Full name</span>
                  <input
                    value={form.full_name}
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                    className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-slate-500 text-xs">Username</span>
                  <input
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                    className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-slate-500 text-xs">Email</span>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
                  />
                </label>
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={saveProfile}
                    disabled={saving}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-sky-600 text-white text-xs font-semibold hover:bg-sky-700 disabled:opacity-50"
                  >
                    <Check className="w-3.5 h-3.5" /> {saving ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    onClick={() => setEditing(false)}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-100 text-slate-600 text-xs font-semibold hover:bg-slate-200"
                  >
                    <X className="w-3.5 h-3.5" /> Cancel
                  </button>
                </div>
              </div>
            )}
          </SectionCard>

          {/* 2. Role & Organization */}
          <SectionCard icon={Building2} title="Role & Organization">
            {!editingRoleOrg ? (
              <>
                <Field label="Role" value={user.role?.replace('_', ' ')} />
                <Field label="Department" value={user.department} />
                <Field label="Organization" value={user.organization} />
                <button
                  onClick={startEditRoleOrg}
                  className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-sky-600 hover:text-sky-700"
                >
                  <Pencil className="w-3.5 h-3.5" /> Edit
                </button>
              </>
            ) : (
              <div className="space-y-3">
                {roleOrgError && <p className="text-xs text-rose-600">{roleOrgError}</p>}
                
                <Field label="Role" value={user.role?.replace('_', ' ')} />

                <label className="block text-sm">
                  <span className="text-slate-500 text-xs">Department</span>
                  <input
                    value={roleOrgForm.department}
                    onChange={(e) => setRoleOrgForm({ ...roleOrgForm, department: e.target.value })}
                    className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-slate-500 text-xs">Organization</span>
                  <input
                    value={roleOrgForm.organization}
                    onChange={(e) => setRoleOrgForm({ ...roleOrgForm, organization: e.target.value })}
                    className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
                  />
                </label>
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={saveRoleOrg}
                    disabled={roleOrgSaving}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-sky-600 text-white text-xs font-semibold hover:bg-sky-700 disabled:opacity-50"
                  >
                    <Check className="w-3.5 h-3.5" /> {roleOrgSaving ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    onClick={() => setEditingRoleOrg(false)}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-100 text-slate-600 text-xs font-semibold hover:bg-slate-200"
                  >
                    <X className="w-3.5 h-3.5" /> Cancel
                  </button>
                </div>
              </div>
            )}
          </SectionCard>

          {/* 3. Security */}
          <SectionCard icon={Shield} title="Security">
            <form onSubmit={submitPasswordChange} className="space-y-3 max-w-sm">
              <p className="text-xs font-semibold text-slate-500 flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5" /> Change Password
              </p>
              {pwError && <p className="text-xs text-rose-600">{pwError}</p>}
              {pwSuccess && <p className="text-xs text-emerald-600">Password updated.</p>}
              <input
                type="password" required placeholder="Current password"
                value={pwForm.current_password}
                onChange={(e) => setPwForm({ ...pwForm, current_password: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
              />
              <input
                type="password" required placeholder="New password (min. 8 characters)"
                value={pwForm.new_password}
                onChange={(e) => setPwForm({ ...pwForm, new_password: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
              />
              <input
                type="password" required placeholder="Confirm new password"
                value={pwForm.confirm}
                onChange={(e) => setPwForm({ ...pwForm, confirm: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
              />
              <button
                type="submit" disabled={pwSaving}
                className="px-3.5 py-1.5 rounded-lg bg-sky-600 text-white text-xs font-semibold hover:bg-sky-700 disabled:opacity-50"
              >
                {pwSaving ? 'Updating...' : 'Update Password'}
              </button>
            </form>
          </SectionCard>

          {/* 4. Session / Account Status */}
          <SectionCard icon={Activity} title="Account Status">
            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-sm font-medium text-slate-700">Status</span>
              <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                user.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'
              }`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <Field label="Last Login" value={formatDateTime(user.last_login_at, user.timezone)} />
          </SectionCard>
        </div>
      </div>
    </Layout>
  );
}