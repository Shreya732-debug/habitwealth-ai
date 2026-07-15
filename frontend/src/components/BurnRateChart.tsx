import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, CartesianGrid } from 'recharts';

interface Props { forecast: any; budget: any; }

export default function BurnRateChart({ forecast, budget }: Props) {
  if (!forecast || !budget) return null;

  const { days_elapsed = 1, days_remaining = 0, total_spent = 0, opening_balance = 0, current_balance = 0, savings_goal = 0 } = budget;
  const burnRate = forecast.burn_rate_per_day ?? 0;

  const data = Array.from({ length: days_elapsed + days_remaining }, (_, i) => ({
    day: i + 1,
    actual:    i < days_elapsed ? Math.round(opening_balance - (total_spent / days_elapsed) * (i + 1)) : null,
    projected: i >= days_elapsed - 1 ? Math.round(current_balance - burnRate * (i - days_elapsed + 1)) : null,
  }));

  const statusColor = forecast.status === 'ON_TRACK' ? '#6BAE75' : forecast.status === 'AT_RISK' ? '#E8A838' : '#E8637A';

  return (
    <div className="bg-white rounded-xl border border-cardBorder p-5">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-medium">Burn rate forecast</h3>
        <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ background: `${statusColor}20`, color: statusColor }}>
          {forecast.status?.replace('_', ' ')}
        </span>
      </div>
      <p className="text-xs text-muted mb-4">₹{Math.round(burnRate).toLocaleString('en-IN')}/day average spend — July 2026</p>
      <ResponsiveContainer width="100%" height={140}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F0EDE8" />
          <XAxis dataKey="day" tick={{ fontSize: 10, fill: '#8A8A9A' }} interval={4} />
          <YAxis tick={{ fontSize: 10, fill: '#8A8A9A' }} tickFormatter={v => `₹${Math.round(v/1000)}k`} />
          <Tooltip formatter={(v: any) => [`₹${Number(v).toLocaleString('en-IN')}`, '']}
            contentStyle={{ background: '#fff', border: '1px solid #E8E4DC', borderRadius: 8, fontSize: 12 }} />
          <ReferenceLine y={savings_goal} stroke="#6BAE75" strokeDasharray="4 4"
            label={{ value: 'Goal', fill: '#6BAE75', fontSize: 10 }} />
          <Line type="monotone" dataKey="actual" stroke="#E8637A" strokeWidth={2} dot={false} connectNulls={false} name="Actual" />
          <Line type="monotone" dataKey="projected" stroke="#9B8EC4" strokeWidth={1.5} strokeDasharray="5 5" dot={false} connectNulls={false} name="Projected" />
        </LineChart>
      </ResponsiveContainer>
      <p className="text-xs mt-2" style={{ color: statusColor }}>{forecast.status_message}</p>
    </div>
  );
}