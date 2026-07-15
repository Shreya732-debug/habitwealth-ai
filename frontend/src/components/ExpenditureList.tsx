import React from 'react';

interface Props { transactions: any[]; onAskAgent: (q: string) => void; }

const CAT_ICONS: Record<string, string> = {
  food:'🍔', transport:'🚗', shopping:'🛒', entertainment:'🎬',
  health:'💊', subscriptions:'📱', education:'📚', utilities:'⚡',
  rent:'🏠', transfer:'💸', income:'💰', other:'📦'
};

export default function ExpenditureList({ transactions, onAskAgent }: Props) {
  const recent = transactions.slice(0, 5);
  return (
    <div className="bg-white rounded-xl border border-cardBorder p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium">Expenditures</h3>
        <span className="text-xs bg-cream border border-cardBorder rounded-full px-3 py-0.5 text-muted">
          {transactions.filter(t => t.amount < 0).length} this month
        </span>
      </div>
      <div className="overflow-y-auto space-y-1" style={{ maxHeight: '320px' }}>
        {recent.length === 0 && <p className="text-xs text-muted">No transactions yet.</p>}
        {recent.map(t => (
          <div key={t.id} className="flex items-center gap-3 py-2.5 border-b border-gray-50 last:border-0">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0"
                 style={{ background: t.amount > 0 ? '#EAF3DE' : '#FAECE7' }}>
              {CAT_ICONS[t.category] ?? '📦'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium truncate">{t.description}</p>
              <p className="text-xs text-muted capitalize">{t.category} · {t.txn_date}</p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <span className={`text-xs font-medium ${t.amount > 0 ? 'text-sage' : 'text-red-500'}`}>
                {t.amount > 0 ? '+' : ''}₹{Math.abs(t.amount).toLocaleString('en-IN')}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${
                t.amount > 0
                  ? 'bg-green-50 text-green-700 border-green-200'
                  : 'bg-red-50 text-red-600 border-red-200'
              }`}>
                {t.amount > 0 ? 'Income' : 'Spent'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}