import React from 'react';

interface Props { budget: any; safeToSpend: any; }

function fmt(n: number) { return `₹${Math.round(n).toLocaleString('en-IN')}`; }

export default function StatCards({ budget, safeToSpend }: Props) {
  const cards = [
    { label: 'Current balance', val: fmt(budget?.current_balance ?? 0), sub: 'This month', color: 'text-coral' },
    { label: 'Savings goal',    val: fmt(budget?.savings_goal ?? 0),    sub: `${budget?.days_remaining ?? 0} days left`, color: 'text-sage' },
    { label: 'Spent this month',val: fmt(budget?.total_spent ?? 0),     sub: `₹${Math.round((budget?.total_spent ?? 0) / Math.max(budget?.days_elapsed ?? 1, 1))}/day avg`, color: 'text-amber' },
    { label: 'Safe to spend today', val: fmt(safeToSpend?.daily_safe_amount ?? 0), sub: safeToSpend?.is_safe ? 'Goal safe ✓' : 'Tight budget ⚠️', color: 'text-lavender' },
  ];

  return (
    <div className="grid grid-cols-4 gap-3">
      {cards.map(c => (
        <div key={c.label} className="bg-white rounded-xl border border-cardBorder p-4">
          <p className="text-xs text-muted mb-1">{c.label}</p>
          <p className={`text-xl font-medium ${c.color}`}>{c.val}</p>
          <p className="text-xs text-muted mt-1">{c.sub}</p>
        </div>
      ))}
    </div>
  );
}