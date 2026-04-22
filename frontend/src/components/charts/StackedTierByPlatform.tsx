import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { chartTooltipProps, useChartPalette } from '@/lib/chartTheme'

export type TierStackRow = { platform: string; hot: number; warm: number; cold: number }

const wrap =
  'h-80 w-full rounded-2xl border border-surface-border bg-premium-card-light p-4 shadow-card transition-colors dark:bg-premium-card-dark lg:h-96'

export function StackedTierByPlatform({ data }: { data: TierStackRow[] }) {
  const p = useChartPalette()
  const tt = chartTooltipProps(p)

  return (
    <div className={wrap}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 12, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={p.grid} vertical={false} />
          <XAxis
            dataKey="platform"
            tick={{ fill: p.tick, fontSize: 11 }}
            axisLine={{ stroke: p.axis }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: p.tick, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip {...tt} />
          <Legend
            wrapperStyle={{ fontSize: 12, color: p.tick }}
            formatter={(v) => (
              <span style={{ color: p.tick }} className="capitalize">
                {v}
              </span>
            )}
          />
          <Bar
            dataKey="hot"
            stackId="t"
            fill={p.hot}
            radius={[0, 0, 0, 0]}
            maxBarSize={44}
            activeBar={{ fill: p.cursorBand }}
          />
          <Bar dataKey="warm" stackId="t" fill={p.warm} maxBarSize={44} activeBar={{ fill: p.cursorBand }} />
          <Bar
            dataKey="cold"
            stackId="t"
            fill={p.cold}
            radius={[8, 8, 0, 0]}
            maxBarSize={44}
            activeBar={{ fill: p.cursorBand }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
