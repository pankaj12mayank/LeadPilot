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
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Settings</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Configure your workspace AI, scraping, and export preferences.
        </p>
      </div>

      <form onSubmit={onSave} className="space-y-6">
        <section className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-white">AI message configuration</h2>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
            Choose how outreach messages are generated. Ollama uses your local or hosted Ollama runtime; API uses an
            OpenAI-compatible HTTPS endpoint.
          </p>

          <div className="mt-4 inline-flex rounded-xl border border-surface-border bg-zinc-50 p-1 dark:bg-zinc-800/50">
            <button
              type="button"
              onClick={() => setAiProvider('ollama')}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium transition ${
                aiProvider === 'ollama'
                  ? 'bg-white text-zinc-900 shadow-sm ring-1 ring-zinc-200 dark:bg-zinc-700 dark:text-white dark:ring-zinc-600'
                  : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200'
              }`}
            >
              Ollama
            </button>
            <button
              type="button"
              onClick={() => setAiProvider('external_api')}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium transition ${
                aiProvider === 'external_api'
                  ? 'bg-white text-zinc-900 shadow-sm ring-1 ring-zinc-200 dark:bg-zinc-700 dark:text-white dark:ring-zinc-600'
                  : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200'
              }`}
            >
              External API
            </button>
          </div>

          <label className="mt-4 flex cursor-pointer items-center gap-3 rounded-xl border border-surface-border bg-zinc-50/50 px-4 py-3 dark:bg-zinc-800/30">
            <input
              type="checkbox"
              checked={freeApi}
              onChange={(e) => setFreeApi(e.target.checked)}
              className="h-4 w-4 rounded border-surface-border accent-amber-600"
            />
            <span className="text-sm text-zinc-600 dark:text-zinc-400">Free API mode (skip all model calls — templates only)</span>
          </label>

          {aiProvider === 'ollama' ? (
            <div className="mt-6 space-y-5">
              <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-surface-border bg-zinc-50/50 px-4 py-3 dark:bg-zinc-800/30">
                <input
                  type="checkbox"
                  checked={useOllama}
                  onChange={(e) => setUseOllama(e.target.checked)}
                  className="h-4 w-4 rounded border-surface-border accent-amber-600"
                />
                <span className="text-sm text-zinc-600 dark:text-zinc-400">Enable Ollama path when not in free API mode</span>
              </label>
              <div>
                <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400" htmlFor="preset">
                  Model preset
                </label>
                <FilterSelect
                  id="preset"
                  className="mt-1.5"
                  options={MODEL_PRESETS}
                  value={modelPreset}
                  onChange={setModelPreset}
                  aria-label="Model preset"
                />
              </div>
              {modelPreset === 'custom' ? (
                <div>
                  <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400" htmlFor="custom">
                    Custom model tag
                  </label>
                  <input
                    id="custom"
                    value={modelCustom}
                    onChange={(e) => setModelCustom(e.target.value)}
                    className="field-input mt-1.5"
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
                    className="rounded-lg border border-surface-border px-3 py-1.5 text-sm font-medium text-zinc-600 transition hover:border-zinc-300 hover:text-zinc-900 disabled:opacity-50 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:text-white"
                  >
                    {ollamaTestBusy ? 'Testing…' : 'Test Ollama connection'}
                  </button>
                  {ollamaTestBusy ? (
                    <span className="text-xs text-zinc-400">
                      Contacting the API — it may start Ollama silently or pull a model (can take up to a few minutes the first time).
                    </span>
                  ) : null}
                </div>
                {ollamaTestMsg ? <p className="text-xs text-zinc-500">{ollamaTestMsg}</p> : null}
                {ollamaTestHints?.length ? (
                  <ul className="max-w-2xl list-disc space-y-1.5 pl-5 text-xs leading-relaxed text-zinc-500">
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
                <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400" htmlFor="ext-url">
                  Chat completions URL
                </label>
                <input
                  id="ext-url"
                  value={extBaseUrl}
                  onChange={(e) => setExtBaseUrl(e.target.value)}
                  className="field-input mt-1.5 font-mono text-xs"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400" htmlFor="ext-key">
                  API key
                </label>
                <input
                  id="ext-key"
                  type="password"
                  autoComplete="off"
                  value={extApiKey}
                  onChange={(e) => setExtApiKey(e.target.value)}
                  className="field-input mt-1.5"
                  placeholder="sk-… or service key"
                />
                <p className="mt-1 text-[11px] text-zinc-400">Leave blank when saving to keep the existing key.</p>
              </div>
              <div>
                <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400" htmlFor="ext-model">
                  Model name
                </label>
                <input
                  id="ext-model"
                  value={extModel}
                  onChange={(e) => setExtModel(e.target.value)}
                  className="field-input mt-1.5"
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
                  className="rounded-lg border border-surface-border px-3 py-1.5 text-sm font-medium text-zinc-600 transition hover:border-zinc-300 hover:text-zinc-900 disabled:opacity-50 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:text-white"
                >
                  {extTestBusy ? 'Testing…' : 'Test API connection'}
                </button>
                {extTestMsg ? <span className="text-xs text-zinc-500">{extTestMsg}</span> : null}
              </div>
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-white">Delay and safety settings</h2>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
            Workspace defaults for prospecting cadence and batch size. Individual runs can still override delays from
            the LinkedIn search screen.
          </p>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div>
              <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Minimum delay (s)</label>
              <input
                type="number"
                step="0.5"
                min={1}
                value={delayMin}
                onChange={(e) => setDelayMin(Number(e.target.value))}
                className="field-input mt-1.5"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Maximum delay (s)</label>
              <input
                type="number"
                step="0.5"
                min={1}
                value={delayMax}
                onChange={(e) => setDelayMax(Number(e.target.value))}
                className="field-input mt-1.5"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Default lead limit</label>
              <input
                type="number"
                min={1}
                max={50}
                value={maxLeads}
                onChange={(e) => setMaxLeads(Number(e.target.value))}
                className="field-input mt-1.5"
              />
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-white">Export preferences</h2>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
            Lead export files use the server export pipeline. Optional directory notes help operators align deployments
            with your data retention policy.
          </p>
          <div className="mt-4 max-w-sm">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400" htmlFor="exports">
              Exports directory (optional note)
            </label>
            <input
              id="exports"
              value={exportsDir}
              onChange={(e) => setExportsDir(e.target.value)}
              className="field-input mt-1.5"
              placeholder="exports"
            />
          </div>
        </section>

        <section className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-white">Account settings</h2>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
            Internal documentation for administrators. Not shown to prospects or external contacts.
          </p>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={4}
            className="field-input mt-4"
          />
        </section>

        {msg ? <p className="text-sm text-zinc-500">{msg}</p> : null}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-amber-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-amber-700 disabled:opacity-50"
          >
            {busy ? 'Saving' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  )
}
