import {
  ResponsiveContainer,
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { CHART_COLORS } from '@/lib/constants'

interface LineChartProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[]
  xKey: string
  lines: { key: string; name?: string; color?: string }[]
  height?: number
  yFormatter?: (v: number) => string
  xFormatter?: (v: string) => string
}

export function LineChart({
  data,
  xKey,
  lines,
  height = 300,
  yFormatter,
  xFormatter,
}: LineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsLineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis
          dataKey={xKey}
          tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
          tickFormatter={xFormatter}
        />
        <YAxis
          tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
          tickFormatter={yFormatter}
          width={70}
        />
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
        {lines.map(({ key, name, color }, i) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            name={name ?? key}
            stroke={color ?? CHART_COLORS[i % CHART_COLORS.length]}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </RechartsLineChart>
    </ResponsiveContainer>
  )
}
