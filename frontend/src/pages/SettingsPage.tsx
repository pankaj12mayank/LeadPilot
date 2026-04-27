import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { ApiLoadError } from '@/components/ui/ApiLoadError'
import { FilterSelect } from '@/components/ui/FilterSelect'
import { getSettings, patchSettings, testExternalApiConnection, testOllamaConnection } from '@/lib/api/settings'
import type { AppSettings } from '@/types/models'

const MODEL_PRESETS = [
  { value: 'qwen2.5:7b', label: 'Qwen 2.5 7B (recommended)' },
  { value: 'llama3.1:8b', label: 'Llama 3.1 8B' },
  { value: 'llama3', label: 'Llama 3' },
  { value: 'mistral', label: 'Mistral' },
  { value: 'phi3', label: 'Phi-3' },
  { value: 'gemma2:9b', label: 'Gemma 2 9B' },
  { value: 'deepseek-r1:8b', label: 'DeepSeek R1 8B' },
  { value: 'custom', label: 'Custom…' },
]

function str(v: unknown) {
  return v === undefined || v === null ? '' : String(v)
}

function boolish(v: unknown, fallback: boolean) {
  if (v === undefined || v === null || v === '') return fallback
  return String(v).toLowerCase() === 'true' || v === true || v === 1 || v === '1'
}

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [modelPreset, setModelPreset] = useState('llama3')
  const [modelCustom, setModelCustom] = useState('')
  const [useOllama, setUseOllama] = useState(true)
  const [freeApi, setFreeApi] = useState(false)
  const [aiProvider, setAiProvider] = useState<'ollama' | 'external_api'>('ollama')
  const [extBaseUrl, setExtBaseUrl] = useState('')
  const [extApiKey, setExtApiKey] = useState('')
  const [extModel, setExtModel] = useState('gpt-4o-mini')
  const [ollamaTestMsg, setOllamaTestMsg] = useState<string | null>(null)
  const [ollamaTestHints, setOllamaTestHints] = useState<string[] | null>(null)
  const [extTestMsg, setExtTestMsg] = useState<string | null>(null)
  const [ollamaTestBusy, setOllamaTestBusy] = useState(false)
  const [extTestBusy, setExtTestBusy] = useState(false)
  const [delayMin, setDelayMin] = useState(3)
  const [delayMax, setDelayMax] = useState(5)
  const [maxLeads, setMaxLeads] = useState(20)
  const [exportsDir, setExportsDir] = useState('')
  const [notes, setNotes] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [settingsBootstrapping, setSettingsBootstrapping] = useState(true)
  const [settingsLoadFailed, setSettingsLoadFailed] = useState(false)
  const [settingsRetryNonce, setSettingsRetryNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    setSettingsBootstrapping(true)
    setSettingsLoadFailed(false)
    setMsg(null)
    ;(async () => {
      try {
        const s = await getSettings()
        if (!cancelled) {
          setSettingsLoadFailed(false)
          setSettings(s)
          const mn = str(s.model_name) || 'llama3'
          const preset = MODEL_PRESETS.find((p) => p.value === mn)?.value
          if (preset && preset !== 'custom') {
            setModelPreset(preset)
            setModelCustom('')
          } else {
            setModelPreset('custom')
            setModelCustom(mn)
          }
          setUseOllama(boolish(s.use_ollama, true))
          setFreeApi(boolish(s.free_api_mode, false))
          const prov = str(s.ai_provider).toLowerCase()
          setAiProvider(prov === 'external_api' ? 'external_api' : 'ollama')
          setExtBaseUrl(str(s.external_api_base_url) || 'https://api.openai.com/v1/chat/completions')
          const ek = str(s.external_api_key)
          setExtApiKey(ek.includes('*') || ek.startsWith('…') ? '' : ek)
          setExtModel(str(s.external_api_model) || 'gpt-4o-mini')
          setDelayMin(Number(s.scraper_delay_min_seconds ?? 3) || 3)
          setDelayMax(Number(s.scraper_delay_max_seconds ?? 5) || 5)
          setMaxLeads(Number(s.scraper_max_leads_default ?? 20) || 20)
          setExportsDir(str(s.exports_dir))
          setNotes(str(s.notes))
        }
      } catch {
        if (!cancelled) {
          setSettings(null)
          setSettingsLoadFailed(true)
          setMsg('Unable to load settings. Check that the API is running, then try again.')
        }
      } finally {
        if (!cancelled) setSettingsBootstrapping(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [settingsRetryNonce])

  async function onSave(e: React.FormEvent) {
    e.preventDefault()
    setMsg(null)
    setBusy(true)
    try {
      const modelName = modelPreset === 'custom' ? modelCustom.trim() : modelPreset
      const patch: Record<string, unknown> = {
        model_name: modelName || undefined,
        use_ollama: useOllama ? 'true' : 'false',
        free_api_mode: freeApi ? 'true' : 'false',
        ai_provider: aiProvider,
        external_api_base_url: extBaseUrl.trim() || undefined,
        external_api_model: extModel.trim() || undefined,
        scraper_delay_min_seconds: delayMin,
        scraper_delay_max_seconds: delayMax,
        scraper_max_leads_default: maxLeads,
        exports_dir: exportsDir.trim() || undefined,
        notes: notes || undefined,
      }
      if (extApiKey.trim()) {
        patch.external_api_key = extApiKey.trim()
      }
      const next = await patchSettings(patch as AppSettings)
      setSettings(next)
      setMsg('Settings saved successfully.')
      toast.success('Settings saved')
    } catch {
      setMsg('Unable to save settings. Verify your connection and try again.')
    } finally {
      setBusy(false)
    }
  }

  if (settingsBootstrapping) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-ink-muted">
        Loading workspace settings
      </div>
    )
  }

  if (settingsLoadFailed || !settings) {
    return (
      <div className="mx-auto max-w-3xl">
        <ApiLoadError
          title="Settings unavailable"
          message={msg ?? 'Workspace settings could not be loaded from the API.'}
          onRetry={() => setSettingsRetryNonce((n) => n + 1)}
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <form onSubmit={onSave} className="space-y-8">
        <section className="rounded-2xl border border-surface-border bg-premium-card-light p-8 shadow-card dark:bg-premium-card-dark">
          <h2 className="type-panel-title mb-2">AI message configuration</h2>
          <p className="text-xs leading-relaxed text-ink-muted">
            Choose how outreach messages are generated. Ollama uses your local or hosted Ollama runtime; API uses an
            OpenAI-compatible HTTPS endpoint.
          </p>

          <div className="mt-6 flex flex-wrap gap-2 rounded-xl border border-surface-border bg-field/40 p-1 dark:bg-zinc-900/40">
            <button
              type="button"
              onClick={() => setAiProvider('ollama')}
              className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition ${
                aiProvider === 'ollama'
                  ? 'bg-gradient-to-r from-amber-600 to-amber-700 text-white shadow-sm'
                  : 'text-ink-muted hover:text-ink'
              }`}
            >
              Ollama
            </button>
            <button
              type="button"
              onClick={() => setAiProvider('external_api')}
              className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition ${
                aiProvider === 'external_api'
                  ? 'bg-gradient-to-r from-amber-600 to-amber-700 text-white shadow-sm'
                  : 'text-ink-muted hover:text-ink'
              }`}
            >
              External API
            </button>
          </div>

          <label className="mt-6 flex cursor-pointer items-center gap-3 rounded-xl border border-surface-border bg-field/60 px-4 py-3 dark:bg-zinc-900/40">
            <input
              type="checkbox"
              checked={freeApi}
              onChange={(e) => setFreeApi(e.target.checked)}
              className="h-4 w-4 rounded border-surface-border bg-field text-amber-700 accent-amber-600 focus:ring-amber-500/30 dark:text-amber-400"
            />
            <span className="text-sm text-ink-muted">Free API mode (skip all model calls — templates only)</span>
          </label>

          {aiProvider === 'ollama' ? (
            <div className="mt-6 space-y-5">
              <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-surface-border bg-field/60 px-4 py-3 dark:bg-zinc-900/40">
                <input
                  type="checkbox"
                  checked={useOllama}
                  onChange={(e) => setUseOllama(e.target.checked)}
                  className="h-4 w-4 rounded border-surface-border bg-field text-amber-700 accent-amber-600 focus:ring-amber-500/30 dark:text-amber-400"
                />
                <span className="text-sm text-ink-muted">Enable Ollama path when not in free API mode</span>
              </label>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="preset">
                  Model preset
                </label>
                <FilterSelect
                  id="preset"
                  className="mt-2"
                  options={MODEL_PRESETS}
                  value={modelPreset}
                  onChange={setModelPreset}
                  aria-label="Model preset"
                />
              </div>
              {modelPreset === 'custom' ? (
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="custom">
                    Custom model tag
                  </label>
                  <input
                    id="custom"
                    value={modelCustom}
                    onChange={(e) => setModelCustom(e.target.value)}
                    className="field-input mt-2"
                    placeholder="e.g. llama3:latest"
                  />
                </div>
              ) : null}
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    disabled={ollamaTestBusy}
                    onClick={async () => {
                      setOllamaTestMsg(null)
                      setOllamaTestHints(null)
                      setOllamaTestBusy(true)
                      try {
                        const modelName = modelPreset === 'custom' ? modelCustom.trim() : modelPreset
                        const r = await testOllamaConnection(modelName || undefined)
                        const sample =
                          r.available_sample?.length && !r.ok
                            ? ` — installed models include e.g. ${r.available_sample.join(', ')}`
                            : ''
                        setOllamaTestMsg(
                          r.ok
                            ? r.auto_started
                              ? `Ollama was not running; the API started it in the background. ${r.detail || 'OK'}`
                              : `Ollama is already running. ${r.detail || 'OK'}`
                            : `Check failed: ${r.detail || 'Unknown'}${sample}`,
                        )
                        setOllamaTestHints(r.hints?.length ? r.hints : null)
                      } catch {
                        setOllamaTestMsg('Test request failed.')
                        setOllamaTestHints(null)
                      } finally {
                        setOllamaTestBusy(false)
                      }
                    }}
                    className="rounded-xl border border-surface-border px-4 py-2 text-sm font-semibold text-ink-muted transition hover:border-amber-500/30 hover:text-ink disabled:opacity-50"
                  >
                    {ollamaTestBusy ? 'Testing…' : 'Test Ollama connection'}
                  </button>
                  {ollamaTestBusy ? (
                    <span className="text-xs text-ink-muted">
                      Contacting the API — it may start Ollama silently or pull a model (can take up to a few minutes the first time).
                    </span>
                  ) : null}
                </div>
                {ollamaTestMsg ? <p className="text-xs text-ink-muted">{ollamaTestMsg}</p> : null}
                {ollamaTestHints?.length ? (
                  <ul className="max-w-2xl list-disc space-y-1.5 pl-5 text-xs leading-relaxed text-ink-muted">
                    {ollamaTestHints.map((h, i) => (
                      <li key={i}>{h}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="mt-6 space-y-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="ext-url">
                  Chat completions URL
                </label>
                <input
                  id="ext-url"
                  value={extBaseUrl}
                  onChange={(e) => setExtBaseUrl(e.target.value)}
                  className="field-input mt-2 font-mono text-xs"
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="ext-key">
                  API key
                </label>
                <input
                  id="ext-key"
                  type="password"
                  autoComplete="off"
                  value={extApiKey}
                  onChange={(e) => setExtApiKey(e.target.value)}
                  className="field-input mt-2"
                  placeholder="sk-… or service key"
                />
                <p className="mt-1 text-[11px] text-ink-subtle">Leave blank when saving to keep the existing key.</p>
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="ext-model">
                  Model name
                </label>
                <input
                  id="ext-model"
                  value={extModel}
                  onChange={(e) => setExtModel(e.target.value)}
                  className="field-input mt-2"
                  placeholder="gpt-4o-mini"
                />
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  disabled={extTestBusy}
                  onClick={async () => {
                    setExtTestMsg(null)
                    setExtTestBusy(true)
                    try {
                      const r = await testExternalApiConnection({
                        api_key: extApiKey.trim() || undefined,
                        base_url: extBaseUrl.trim() || undefined,
                        model: extModel.trim() || undefined,
                      })
                      setExtTestMsg(r.ok ? `Connected: ${r.detail || 'OK'}` : `Failed: ${r.detail || 'Unknown'}`)
                    } catch {
                      setExtTestMsg('Test request failed.')
                    } finally {
                      setExtTestBusy(false)
                    }
                  }}
                  className="rounded-xl border border-surface-border px-4 py-2 text-sm font-semibold text-ink-muted transition hover:border-amber-500/30 hover:text-ink disabled:opacity-50"
                >
                  {extTestBusy ? 'Testing…' : 'Test API connection'}
                </button>
                {extTestMsg ? <span className="text-xs text-ink-muted">{extTestMsg}</span> : null}
              </div>
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-surface-border bg-premium-card-light p-8 shadow-card dark:bg-premium-card-dark">
          <h2 className="type-panel-title mb-2">Delay and safety settings</h2>
          <p className="mt-2 text-xs leading-relaxed text-ink-muted">
            Workspace defaults for prospecting cadence and batch size. Individual runs can still override delays from
            the LinkedIn search screen.
          </p>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Minimum delay (s)</label>
              <input
                type="number"
                step="0.5"
                min={1}
                value={delayMin}
                onChange={(e) => setDelayMin(Number(e.target.value))}
                className="field-input mt-2"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Maximum delay (s)</label>
              <input
                type="number"
                step="0.5"
                min={1}
                value={delayMax}
                onChange={(e) => setDelayMax(Number(e.target.value))}
                className="field-input mt-2"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Default lead limit</label>
              <input
                type="number"
                min={1}
                max={50}
                value={maxLeads}
                onChange={(e) => setMaxLeads(Number(e.target.value))}
                className="field-input mt-2"
              />
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-surface-border bg-premium-card-light p-8 shadow-card dark:bg-premium-card-dark">
          <h2 className="type-panel-title mb-2">Export preferences</h2>
          <p className="mt-2 text-xs leading-relaxed text-ink-muted">
            Lead export files use the server export pipeline. Optional directory notes help operators align deployments
            with your data retention policy.
          </p>
          <div className="mt-6">
            <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="exports">
              Exports directory (optional note)
            </label>
            <input
              id="exports"
              value={exportsDir}
              onChange={(e) => setExportsDir(e.target.value)}
              className="field-input mt-2"
              placeholder="exports"
            />
          </div>
        </section>

        <section className="rounded-2xl border border-surface-border bg-premium-card-light p-8 shadow-card dark:bg-premium-card-dark">
          <h2 className="type-panel-title mb-2">Account settings</h2>
          <p className="text-xs leading-relaxed text-ink-muted">
            Internal documentation for administrators. Not shown to prospects or external contacts.
          </p>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={4}
            className="field-input mt-4"
          />
        </section>

        {msg ? <p className="text-sm text-ink-muted">{msg}</p> : null}

        <button
          type="submit"
          disabled={busy}
          className="btn-primary px-6 py-3 text-sm disabled:opacity-50"
        >
          {busy ? 'Saving' : 'Save Changes'}
        </button>
      </form>
    </div>
  )
}
