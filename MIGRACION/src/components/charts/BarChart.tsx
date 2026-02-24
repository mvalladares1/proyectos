import {
  ResponsiveContainer,
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
} from 'recharts'
import { CHART_COLORS } from '@/lib/constants'

interface BarChartProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[]
  xKey: string
  bars: { key: string; name?: string; color?: string }[]
  height?: number
  stacked?: boolean
  horizontal?: boolean
  yFormatter?: (v: number) => string
  xFormatter?: (v: string) => string
}

export function BarChart({
  data,
  xKey,
  bars,
  height = 300,
  stacked = false,
  horizontal = false,
  yFormatter,
  xFormatter,
}: BarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart
        data={data}
        layout={horizontal ? 'vertical' : 'horizontal'}
        margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        {horizontal ? (
          <>
            <YAxis dataKey={xKey} type="category" tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} width={120} tickFormatter={xFormatter} />
            <XAxis type="number" tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} tickFormatter={yFormatter} />
          </>
        ) : (
          <>
            <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} tickFormatter={xFormatter} />
            <YAxis tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} tickFormatter={yFormatter} width={70} />
          </>
        )}
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '0.5rem',
            color: 'hsl(var(--foreground))',
            fontSize: 12,
          }}
          formatter={(value: number, name: string) => [
            yFormatter ? yFormatter(value) : value,
            name,
          ]}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {bars.map(({ key, name, color }, i) => (
          <Bar
            key={key}
            dataKey={key}
            name={name ?? key}
            fill={color ?? CHART_COLORS[i % CHART_COLORS.length]}
            stackId={stacked ? 'stack' : undefined}
            radius={stacked ? [0, 0, 0, 0] : [3, 3, 0, 0]}
          />
        ))}
      </RechartsBarChart>
    </ResponsiveContainer>
  )
}
