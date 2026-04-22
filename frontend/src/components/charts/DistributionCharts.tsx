import { memo } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { chartTooltipProps, useChartPalette } from '@/lib/chartTheme'

type Datum = { name: string; value: number }

const chartClass =
  'h-80 w-full rounded-2xl border border-surface-border bg-premium-card-light p-4 shadow-card transition-colors dark:bg-premium-card-dark lg:h-96'

export const PlatformBar = memo(function PlatformBar({ data }: { data: Datum[] }) {
  const p = useChartPalette()
  const tt = chartTooltipProps(p)

  return (
    <div className={chartClass}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 12, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={p.grid} vertical={false} />
          <XAxis
            dataKey="name"
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
          <Bar
            dataKey="value"
            fill={p.barPrimary}
            radius={[8, 8, 0, 0]}
            maxBarSize={48}
            activeBar={{ fill: p.cursorBand }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
})

export const StatusPie = memo(function StatusPie({ data }: { data: Datum[] }) {
  const p = useChartPalette()
  const tt = chartTooltipProps(p)

  return (
    <div className={chartClass}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={68}
            outerRadius={110}
            paddingAngle={2}
            stroke="transparent"
          >
            {data.map((_, i) => (
              <Cell key={i} fill={p.pie[i % p.pie.length]} stroke="transparent" />
            ))}
          </Pie>
          <Legend
            wrapperStyle={{ fontSize: 12, color: p.tick }}
            formatter={(value) => <span style={{ color: p.tick }}>{value}</span>}
          />
          <Tooltip {...tt} cursor={false} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
})