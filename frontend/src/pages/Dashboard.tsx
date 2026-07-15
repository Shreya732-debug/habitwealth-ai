import React, { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useFinanceData } from '../hooks/useFinanceData';
import Sidebar         from '../components/Sidebar';
import StatCards       from '../components/StatCards';
import BurnRateChart   from '../components/BurnRateChart';
import SavingsChart    from '../components/SavingsChart';
import ExpenditureList from '../components/ExpenditureList';
import LeisureList     from '../components/LeisureList';
import CalendarPanel   from '../components/CalendarPanel';
import ChatPanel       from '../components/ChatPanel';

export default function Dashboard() {
  const navigate = useNavigate();

  // Single declaration — includes refreshing from the updated hook
  const {
    budget,
    transactions,
    safeToSpend,
    forecast,
    health,
    categories,
    loading,
    refreshing,
    error,
    refetch,
  } = useFinanceData();

  const [activeTab, setActiveTab] = useState<'overview' | 'chat'>('overview');

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    navigate('/login');
  };

  // Simple — just calls refetch, no extra state needed
  const handleRefresh = () => refetch();

  const askAgent = (q: string) => {
    setActiveTab('chat');
  };

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? 'Good morning' :
    hour < 17 ? 'Good afternoon' : 'Good evening';

  // Only show loading screen on very first load (no data yet)
  if (loading && !budget) return (
    <div className="min-h-screen bg-cream flex items-center justify-center">
      <div className="text-center">
        <div className="text-5xl mb-4">💰</div>
        <p className="text-muted text-sm">Loading your finances...</p>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-cream overflow-hidden">

      {/* SIDEBAR */}
      <div className="w-52 flex-shrink-0 h-full">
        <Sidebar onLogout={handleLogout} />
      </div>

      {/* MAIN SCROLL AREA */}
      <main className="flex-1 overflow-y-auto px-6 py-5 min-w-0">

        {/* GREETING */}
        <div className="flex items-start justify-between mb-5">
          <div>
            <h1 className="text-xl font-medium text-gray-900">
              {greeting}, Shreya 👋
            </h1>
            <p className="text-sm text-muted mt-0.5">
              {transactions.filter((t: any) => t.amount < 0).length} expenses recorded
              · {budget?.days_remaining ?? 0} days left this month
            </p>
            <div className="flex items-center gap-2 mt-2">
              <span className="pulse-dot" />
              <span className="text-xs text-sage font-medium">
                Health score: {health?.health_score ?? 0}/100 — {health?.summary}
              </span>
            </div>
          </div>

          {/* Refresh button — spins during background refresh */}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 text-muted hover:text-coral transition-colors rounded-lg hover:bg-white"
            title="Refresh data"
          >
            <RefreshCw
              size={15}
              className={refreshing ? 'animate-spin' : ''}
            />
          </button>
        </div>

        {/* TABS */}
        <div className="flex gap-1 mb-5 bg-white border border-cardBorder rounded-lg p-1 w-fit">
          {(['overview', 'chat'] as const).map(t => (
            <button
              key={t}
              type="button"
              onClick={() => setActiveTab(t)}
              className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === t
                  ? 'bg-coral text-white'
                  : 'text-muted hover:text-gray-900'
              }`}
            >
              {t === 'chat' ? 'Ask FinanceGPT' : 'Overview'}
            </button>
          ))}
        </div>

        {/* OVERVIEW TAB */}
        <div style={{ display: activeTab === 'overview' ? 'block' : 'none' }}>
          <div className="space-y-4">
            <StatCards budget={budget} safeToSpend={safeToSpend} />
            <div className="grid grid-cols-2 gap-4">
              <BurnRateChart forecast={forecast} budget={budget} />
              <SavingsChart
                savingsGoal={budget?.savings_goal ?? 5000}
                currentSaved={Math.max(
                  0,
                  (budget?.current_balance ?? 0) - (budget?.savings_goal ?? 0)
                )}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <ExpenditureList
                transactions={transactions}
                onAskAgent={askAgent}
              />
              <LeisureList
                onAskAgent={askAgent}
                onRefetch={refetch}
              />
            </div>
          </div>
        </div>

        {/* CHAT TAB — always rendered, never unmounted */}
        <div
          style={{
            display: activeTab === 'chat' ? 'block' : 'none',
            height: 'calc(100vh - 200px)',
          }}
        >
          <ChatPanel onAnswered={refetch} />
        </div>

      </main>

      {/* RIGHT PANEL — Calendar */}
      <div className="w-72 flex-shrink-0 h-full overflow-y-auto">
        <CalendarPanel
          transactions={transactions}
          forecast={forecast}
          budget={budget}
          health={health}
        />
      </div>
    </div>
  );
}
