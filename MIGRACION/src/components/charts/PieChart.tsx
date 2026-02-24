import {
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from 'recharts'
import { CHART_COLORS } from '@/lib/constants'

interface PieChartProps {
  data: { name: string; value: number; color?: string }[]
  height?: number
  donut?: boolean
  formatter?: (v: number) => string
}

export function PieChart({ data, height = 300, donut = false, formatter }: PieChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsPieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          innerRadius={donut ? '40%' : 0}
          outerRadius="70%"
          paddingAngle={2}
        >
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.color ?? CHART_COLORS[index % CHART_COLORS.length]}
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '0.5rem',
            color: 'hsl(var(--foreground))',
            fontSize: 12,
          }}
          formatter={(value: number, name: string) => [
            formatter ? formatter(value) : value,
            name,
          ]}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </RechartsPieChart>
    </ResponsiveContainer>
  )
}
