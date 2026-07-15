import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';

interface Props { transactions: any[]; forecast: any; budget: any; health: any; }

export default function CalendarPanel({ transactions, forecast, budget, health }: Props) {
  const [viewDate,     setViewDate]     = useState(new Date(2026, 6, 1));
  const [selectedDay,  setSelectedDay]  = useState<number | null>(null);

  const yr  = viewDate.getFullYear();
  const mo  = viewDate.getMonth();

  const prevMonth = () => setViewDate(new Date(yr, mo - 1, 1));
  const nextMonth = () => setViewDate(new Date(yr, mo + 1, 1));

  const MONTHS = ['January','February','March','April','May','June',
                  'July','August','September','October','November','December'];

  // Build calendar days
  const firstDow   = (new Date(yr, mo, 1).getDay() + 6) % 7; // Mon=0
  const daysInMo   = new Date(yr, mo + 1, 0).getDate();
  const daysInPrev = new Date(yr, mo,     0).getDate();

  const cells: { day: number; curr: boolean }[] = [];
  for (let i = firstDow - 1; i >= 0; i--)
    cells.push({ day: daysInPrev - i, curr: false });
  for (let d = 1; d <= daysInMo; d++)
    cells.push({ day: d, curr: true });
  while (cells.length % 7 !== 0)
    cells.push({ day: cells.length - daysInMo - firstDow + 1, curr: false });

  // Which dates have transactions this month
  const txnByDay: Record<number, any[]> = {};
  transactions.forEach(t => {
    const d = new Date(t.txn_date);
    if (d.getFullYear() === yr && d.getMonth() === mo) {
      const day = d.getDate();
      txnByDay[day] = txnByDay[day] || [];
      txnByDay[day].push(t);
    }
  });

  // Upcoming dates (hardcoded for demo — in production these come from commitments)
  const upcomingDates = new Set([12, 14, 15, 18, 20]);
  const today = new Date();
  const isCurrentMonth = today.getFullYear() === yr && today.getMonth() === mo;
  const todayDay = today.getDate();

  const scoreColor = (health?.health_score ?? 100) >= 80 ? '#6BAE75'
                   : (health?.health_score ?? 100) >= 50 ? '#E8A838' : '#E8637A';

  // Day detail panel
  const selectedTxns = selectedDay ? (txnByDay[selectedDay] || []) : [];
  const selectedTotal = selectedTxns.reduce((s: number, t: any) => s + t.amount, 0);

  return (
    <div className="bg-white border-l border-cardBorder h-full flex flex-col overflow-hidden">
      <div className="p-5 flex-shrink-0">

        {/* Calendar nav */}
        <div className="flex items-center justify-between mb-3">
          <button onClick={prevMonth}
            className="p-1.5 rounded-lg hover:bg-cream text-muted hover:text-coral transition-all">
            <ChevronLeft size={14} />
          </button>
          <span className="text-sm font-medium text-coral">
            {MONTHS[mo]} {yr}
          </span>
          <button onClick={nextMonth}
            className="p-1.5 rounded-lg hover:bg-cream text-muted hover:text-coral transition-all">
            <ChevronRight size={14} />
          </button>
        </div>

        {/* Day-of-week headers */}
        <div className="grid grid-cols-7 gap-0.5 text-center mb-1">
          {['Mo','Tu','We','Th','Fr','Sa','Su'].map(d => (
            <div key={d} className="text-xs text-muted py-1 font-medium">{d}</div>
          ))}
        </div>

        {/* Days grid */}
        <div className="grid grid-cols-7 gap-0.5 text-center">
          {cells.map((c, i) => {
            const isToday    = c.curr && isCurrentMonth && c.day === todayDay;
            const hasData    = c.curr && txnByDay[c.day]?.length > 0;
            const isUpcoming = c.curr && upcomingDates.has(c.day);
            const isSelected = c.curr && selectedDay === c.day;

            return (
              <div key={i}
                onClick={() => c.curr && setSelectedDay(selectedDay === c.day ? null : c.day)}
                className={`relative text-xs py-1.5 rounded-md transition-all select-none ${
                  c.curr ? 'cursor-pointer' : 'cursor-default'
                } ${
                  isSelected ? 'ring-2 ring-coral ring-offset-1'
                  : isToday ? 'bg-coral text-white font-medium'
                  : isUpcoming ? 'bg-amber/20 text-amber font-medium'
                  : c.curr ? 'text-gray-700 hover:bg-cream'
                  : 'text-muted/40'
                }`}>
                {c.day}
                {hasData && !isToday && (
                  <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-sage block" />
                )}
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex gap-3 mt-3 flex-wrap">
          <div className="flex items-center gap-1.5 text-xs text-muted">
            <span className="w-2 h-2 rounded-full bg-sage inline-block" /> Activity
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted">
            <span className="w-2 h-2 rounded bg-amber/40 inline-block" /> Upcoming
          </div>
        </div>
      </div>

      {/* DAY DETAIL PANEL — shows when a day is clicked */}
      {selectedDay && (
        <div className="mx-4 mb-3 bg-cream border border-cardBorder rounded-xl p-3 flex-shrink-0">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-medium text-gray-800">
              {MONTHS[mo]} {selectedDay}
            </p>
            <button onClick={() => setSelectedDay(null)}
              className="text-muted hover:text-gray-700 transition-colors">
              <X size={12} />
            </button>
          </div>

          {selectedTxns.length === 0 ? (
            <p className="text-xs text-muted">No activity on this day.</p>
          ) : (
            <>
              <div className="space-y-1.5 max-h-32 overflow-y-auto">
                {selectedTxns.map((t: any, i: number) => (
                  <div key={i} className="flex items-center justify-between">
                    <p className="text-xs text-gray-700 truncate max-w-[140px]">{t.description}</p>
                    <span className={`text-xs font-medium ${t.amount > 0 ? 'text-sage' : 'text-red-500'}`}>
                      {t.amount > 0 ? '+' : ''}₹{Math.abs(t.amount).toLocaleString('en-IN')}
                    </span>
                  </div>
                ))}
              </div>
              <div className="border-t border-cardBorder mt-2 pt-2 flex justify-between">
                <span className="text-xs text-muted">Day total</span>
                <span className={`text-xs font-medium ${selectedTotal > 0 ? 'text-sage' : 'text-red-500'}`}>
                  {selectedTotal > 0 ? '+' : ''}₹{Math.abs(selectedTotal).toLocaleString('en-IN')}
                </span>
              </div>
            </>
          )}
        </div>
      )}

      {/* SCROLLABLE LOWER SECTION */}
      <div className="flex-1 overflow-y-auto px-5 pb-5 border-t border-cardBorder">

        {/* Daily log */}
        <div className="pt-4">
          <p className="text-xs font-medium text-muted uppercase tracking-wider mb-3">
            {isCurrentMonth ? `Today — ${MONTHS[mo]} ${todayDay}` : `${MONTHS[mo]} ${yr}`}
          </p>
          {[
            { color: '#6BAE75', label: 'Balance',       val: `₹${Math.round(budget?.current_balance ?? 0).toLocaleString('en-IN')}` },
            { color: '#E8637A', label: 'Burn rate',     val: `₹${Math.round(forecast?.burn_rate_per_day ?? 0)}/day` },
            { color: '#E8A838', label: 'Days left',     val: `${budget?.days_remaining ?? 0} days` },
            { color: '#9B8EC4', label: 'Projected end', val: `₹${Math.round(forecast?.projected_month_end_balance ?? 0).toLocaleString('en-IN')}` },
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-2.5 mb-3">
              <span className="w-2 h-2 rounded-full mt-1 flex-shrink-0"
                    style={{ background: item.color }} />
              <div>
                <p className="text-xs font-medium text-gray-800">{item.label}</p>
                <p className="text-xs text-muted">{item.val}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Health meter */}
        <div className="border-t border-cardBorder pt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium">Financial health</span>
            <span className="text-sm font-medium" style={{ color: scoreColor }}>
              {health?.health_score ?? 0}/100
            </span>
          </div>
          <div className="bg-cream rounded-full h-2 mb-1">
            <div className="h-2 rounded-full transition-all duration-700"
                 style={{ width: `${health?.health_score ?? 0}%`, background: scoreColor }} />
          </div>
          <div className="flex justify-between text-xs text-muted mb-3">
            <span>Critical</span><span>At risk</span><span>Good</span>
          </div>
          {health?.alerts?.length > 0
            ? health.alerts.slice(0,2).map((a: any, i: number) => (
                <div key={i} className={`text-xs p-2.5 rounded-lg mb-2 ${
                  a.severity === 'CRITICAL' ? 'bg-red-50 text-red-700 border border-red-200'
                  : a.severity === 'HIGH'   ? 'bg-orange-50 text-orange-700 border border-orange-200'
                  : 'bg-amber/10 text-amber border border-amber/30'
                }`}>{a.message}</div>
              ))
            : <div className="bg-green-50 border border-green-200 rounded-lg p-2.5 text-xs text-green-700">
                {health?.summary}
              </div>
          }
        </div>
      </div>
    </div>
  );
}