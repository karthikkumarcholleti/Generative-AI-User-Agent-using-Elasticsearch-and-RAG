import { PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444'];

export default function GenderPieChart({ data }: { data: { gender: string, count: number }[] }) {
  return (
    <div className="bg-white p-5 rounded-xl shadow border">
      <h2 className="text-sm text-gray-500 mb-2">Gender Breakdown</h2>
      <PieChart width={300} height={250}>
        <Pie data={data} dataKey="count" nameKey="gender" cx="50%" cy="50%" outerRadius={80} label>
          {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </div>
  );
}
