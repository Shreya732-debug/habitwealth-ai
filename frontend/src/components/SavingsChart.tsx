import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts';

interface Props { savingsGoal: number; currentSaved: number; }

export default function SavingsChart({ savingsGoal, currentSaved }: Props) {
  const months = ['Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'];
  const mockActual = [4200, 5800, 3100, 5200, 4800, currentSaved];

  const data = months.map((m, i) => ({ month: m, goal: savingsGoal, actual: mockActual[i] }));

  return (
    <div className="bg-white rounded-xl border border-cardBorder p-5">
      <h3 className="text-sm font-medium mb-1">Savings consistency</h3>
      <p className="text-xs text-muted mb-4">Monthly goal vs actual saved — last 6 months</p>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={data} barGap={2}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F0EDE8" vertical={false} />
          <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#8A8A9A' }} />
          <YAxis tick={{ fontSize: 10, fill: '#8A8A9A' }} tickFormatter={v => `₹${v/1000}k`} />
          <Tooltip formatter={(v: any) => [`₹${Number(v).toLocaleString('en-IN')}`, '']}
            contentStyle={{ background: '#fff', border: '1px solid #E8E4DC', borderRadius: 8, fontSize: 12 }} />
          <ReferenceLine y={savingsGoal} stroke="#E8A838" strokeDasharray="4 4" />
          <Bar dataKey="actual" fill="#6BAE75" radius={[4,4,0,0]} name="Saved" 
          label={({ value }) => Number(value) >= savingsGoal ? '✓' : ''} />
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs text-amber mt-2">
        {currentSaved < savingsGoal
          ? `⚠️ July savings ${Math.round((1 - currentSaved/savingsGoal)*100)}% below goal — ${data[5] ? '' : ''}act now`
          : '✅ On track for July goal'}
      </p>
    </div>
  );
}