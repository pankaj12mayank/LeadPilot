import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'

import {
  adminGetControls,
  adminPatchControls,
  type AdminControls,
} from '@/lib/api/admin'
import { getApiErrorMessage } from '@/lib/api/client'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Save } from 'lucide-react'

const weightLabels: Record<keyof AdminControls['scoring_weights'], string> = {
  role_relevance: 'Role Relevance',
  company_size: 'Company Size',
  signals: 'Signals & Intent',
  data_completeness: 'Data Completeness',
  base_factor_mix: 'Base Factor Mix',
}

const weightDescriptions: Record<keyof AdminControls['scoring_weights'], string> = {
  role_relevance: 'How well the lead\'s job title matches your target persona',
  company_size: 'Company employee count and revenue indicators',
  signals: 'Hiring, scaling, and content gap signals',
  data_completeness: 'Profile completeness and data quality',
  base_factor_mix: 'Baseline score factor for all leads',
}

export function AdminScoringPage() {
  const [controls, setControls] = useState<AdminControls | null>(null)
  const [dirty, setDirty] = useState(false)
  const [showSave, setShowSave] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      setControls(await adminGetControls())
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Could not load controls'))
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function saveAll() {
    if (!controls) return
    setSaving(true)
    try {
      const next = await adminPatchControls({
        scoring_weights: controls.scoring_weights,
        schedule_timing: controls.schedule_timing,
      })
      setControls(next)
      setDirty(false)
      setShowSave(false)
      toast.success('Scoring & schedule saved')
    } catch (e) { toast.error(getApiErrorMessage(e, 'Could not save')) }
    finally { setSaving(false) }
  }

  function updateWeight(key: keyof AdminControls['scoring_weights'], value: number) {
    if (!controls) return
    setControls({ ...controls, scoring_weights: { ...controls.scoring_weights, [key]: value } })
    setDirty(true)
  }

  function updateSchedule(key: keyof AdminControls['schedule_timing'], value: string) {
    if (!controls) return
    setControls({ ...controls, schedule_timing: { ...controls.schedule_timing, [key]: value } })
    setDirty(true)
  }

  function cronToTime(cron: string): string {
    const p = String(cron || '').trim().split(/\s+/)
    if (p.length < 2) return '06:00'
    const hh = /^\d+$/.test(p[1]) ? String(Math.max(0, Math.min(23, Number(p[1])))).padStart(2, '0') : '06'
    const mm = /^\d+$/.test(p[0]) ? String(Math.max(0, Math.min(59, Number(p[0])))).padStart(2, '0') : '00'
    return `${hh}:${mm}`
  }

  function timeToCron(val: string): string {
    const [h = '6', m = '0'] = val.split(':')
    return `${m} ${h} * * *`
  }

  if (!controls) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500/30 border-t-amber-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Scoring & Schedule</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Configure lead scoring weights and automated job timing</p>
        </div>
        <button
          type="button"
          disabled={!dirty}
          onClick={() => setShowSave(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-700 disabled:opacity-45"
        >
          <Save className="h-4 w-4" />
          Save Changes
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Scoring Weights */}
        <div className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
          <div className="mb-6">
            <h2 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">Scoring Weights</h2>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Drag sliders to set the importance of each scoring factor</p>
          </div>
          <div className="space-y-6">
            {(Object.entries(controls.scoring_weights) as [string, number][]).map(([k, v]) => (
              <div key={String(k)}>
                <div className="mb-1 flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">{weightLabels[k]}</span>
                    <p className="text-xs text-zinc-400 dark:text-zinc-500">{weightDescriptions[k]}</p>
                  </div>
                  <span className="ml-4 flex h-8 w-14 items-center justify-center rounded-lg border border-surface-border bg-zinc-50 font-mono text-sm font-bold text-amber-700 dark:bg-zinc-800 dark:text-amber-300">
                    {v}%
                  </span>
                </div>
                <input
                  type="range" min={1} max={100} value={v}
                  onChange={(e) => updateWeight(k, Number(e.target.value))}
                  className="mt-2 h-2 w-full cursor-pointer appearance-none rounded-full bg-zinc-200 accent-amber-600 dark:bg-zinc-700"
                  style={{
                    background: `linear-gradient(to right, #d97706 ${v}%, #e5e7eb ${v}%)`,
                  }}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Schedule Timing */}
        <div className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
          <div className="mb-6">
            <h2 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">Schedule Timing</h2>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Set when automated jobs should run</p>
          </div>
          <div className="space-y-5">
            {(Object.entries(controls.schedule_timing) as [string, string][]).map(([k, v]) => {
              const labels: Record<string, string> = {
                daily_auto: 'Daily Auto',
                friday_heavy: 'Friday Heavy',
                saturday_linkedin: 'Saturday LinkedIn',
                sunday_report: 'Sunday Report',
              }
              const descs: Record<string, string> = {
                daily_auto: 'Standard daily lead processing',
                friday_heavy: 'Full enrichment and scoring run every Friday',
                saturday_linkedin: 'LinkedIn-specific outreach jobs on Saturday',
                sunday_report: 'Weekly summary report generation',
              }
              return (
                <label key={k} className="block">
                  <div className="mb-1 flex items-center justify-between">
                    <div>
                      <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">{labels[k] || k}</span>
                      <p className="text-xs text-zinc-400 dark:text-zinc-500">{descs[k] || ''}</p>
                    </div>
                    <span className="ml-2 text-xs font-mono text-zinc-500 dark:text-zinc-400">{v}</span>
                  </div>
                  <input
                    type="time"
                    value={cronToTime(v)}
                    onChange={(e) => updateSchedule(k, timeToCron(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-surface-border bg-zinc-50 px-3 py-2 text-sm dark:bg-zinc-800 dark:text-zinc-100"
                  />
                </label>
              )
            })}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={showSave}
        title="Save Scoring & Schedule"
        message="Are you sure you want to save these changes? This will update the scoring weights and scheduling configuration for all leads."
        confirmLabel="Save Changes"
        variant="default"
        busy={saving}
        onConfirm={() => void saveAll()}
        onCancel={() => setShowSave(false)}
      />
    </div>
  )
}
