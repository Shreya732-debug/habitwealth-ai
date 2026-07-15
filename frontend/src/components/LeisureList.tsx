import React, { useState } from 'react';
import { Zap, Check } from 'lucide-react';
import API from '../api';

interface LeisureItem {
  icon: string; label: string; category: string;
  amount: number; done: boolean; date: string;
}

interface Props {
  onAskAgent: (q: string) => void;
  onRefetch?: () => void;
}

const DEFAULT_ITEMS: LeisureItem[] = [
  { icon:'🎬', label:'Movie night',         category:'entertainment', amount:350,  done:false, date:'Planned Jul 12' },
  { icon:'🍽️', label:'Dinner date',          category:'dine out',     amount:1200, done:false, date:'Planned Jul 14' },
  { icon:'💅', label:'Manicure + pedicure', category:'self care',     amount:600,  done:true,  date:'Done Jul 6' },
  { icon:'🎂', label:"Friend's birthday",    category:'birthday',     amount:500,  done:false, date:'Jul 18' },
  { icon:'🎭', label:'Escape room',          category:'entertainment', amount:800,  done:false, date:'Planned' },
  { icon:'💆', label:'Facial + spa',         category:'self care',     amount:1500, done:false, date:'Planned' },
  { icon:'🛍️', label:'Shopping haul',        category:'shopping',     amount:2000, done:false, date:'Planned' },
  { icon:'🎉', label:'Anniversary dinner',   category:'dine out',     amount:3000, done:false, date:'Planned' },
];

export default function LeisureList({ onAskAgent, onRefetch }: Props) {
  const [items,    setItems]    = useState(DEFAULT_ITEMS);
  const [toggling, setToggling] = useState<number | null>(null);

  const toggle = async (idx: number) => {
    const item = items[idx];
    setToggling(idx);
    try {
      if (!item.done) {
        // Record the expense in the backend when marking done
        await API.post('/transactions/add', {
          amount:      -item.amount,
          description: item.label,
          category:    item.category,
          txn_date:    new Date().toISOString().split('T')[0],
        });
        // Refetch dashboard data so balance/burn rate updates
        onRefetch?.();
      }
      setItems(prev => prev.map((it, i) =>
        i === idx ? { ...it, done: !it.done } : it
      ));
    } catch (e) {
      console.error('Failed to record leisure expense', e);
    } finally {
      setToggling(null);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-cardBorder p-5 flex flex-col">
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h3 className="text-sm font-medium">Leisure & plans</h3>
        <span className="text-xs bg-cream border border-cardBorder rounded-full px-3 py-0.5 text-muted">
          {items.filter(i => !i.done).length} pending
        </span>
      </div>

      {/* Scrollable list — fixed height */}
      <div className="overflow-y-auto" style={{ maxHeight: '320px' }}>
        {items.map((item, idx) => (
          <div key={idx}
            className="flex items-center gap-3 py-2.5 border-b border-gray-50 last:border-0">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0 bg-cream">
              {item.icon}
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-xs font-medium truncate ${item.done ? 'line-through text-muted' : ''}`}>
                {item.label}
              </p>
              <p className="text-xs text-muted">{item.category} · {item.date}</p>
            </div>
            <div className="flex flex-col items-end gap-1 flex-shrink-0">
              <span className="text-xs font-medium text-muted">
                ~₹{item.amount.toLocaleString('en-IN')}
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => toggle(idx)}
                  disabled={toggling === idx}
                  className={`text-xs px-2 py-0.5 rounded-full border transition-all flex items-center gap-1 ${
                    item.done
                      ? 'bg-green-50 text-green-700 border-green-200'
                      : 'bg-orange-50 text-orange-600 border-orange-200 hover:bg-green-50 hover:text-green-700 hover:border-green-200'
                  }`}>
                  {toggling === idx ? '...' : item.done ? <><Check size={9} /> Done</> : 'Mark done'}
                </button>
                {!item.done && (
                  <button
                    onClick={() => onAskAgent(
                      `Can I afford ${item.label} for ₹${item.amount} and still hit my ₹5000 savings goal?`
                    )}
                    className="text-coral hover:text-coral/70 transition-colors"
                    title="Check affordability">
                    <Zap size={12} />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}