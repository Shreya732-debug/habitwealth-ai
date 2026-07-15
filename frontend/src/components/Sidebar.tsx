import React from 'react';
import { LayoutDashboard, Calendar, Receipt, Sparkles, TrendingUp, PieChart, FileText, Bot, ShoppingCart, Settings, LogOut } from 'lucide-react';

const navItems = [
  { section: 'General', items: [
    { icon: LayoutDashboard, label: 'Dashboard', active: true },
    { icon: Calendar,        label: 'Calendar' },
    { icon: Receipt,         label: 'Expenses' },
    { icon: Sparkles,        label: 'Leisure' },
  ]},
  { section: 'Analytics', items: [
    { icon: TrendingUp, label: 'Savings track' },
    { icon: PieChart,   label: 'Category split' },
    { icon: FileText,   label: 'Statements' },
  ]},
  { section: 'Tools', items: [
    { icon: Bot,          label: 'Ask FinanceGPT' },
    { icon: ShoppingCart, label: 'Buy advisor' },
    { icon: Settings,     label: 'Settings' },
  ]},
];

export default function Sidebar({ onLogout }: { onLogout: () => void }) {
  return (
    <div className="bg-sidebar text-white flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-white/10">
        <div className="w-8 h-8 bg-coral rounded-lg flex items-center justify-center text-base">💰</div>
        <span className="font-medium text-white">FinanceGPT</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        {navItems.map(section => (
          <div key={section.section} className="mb-4">
            <p className="text-xs text-white/30 font-medium uppercase tracking-widest px-2 mb-2">
              {section.section}
            </p>
            {section.items.map(item => (
              <div key={item.label}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer mb-0.5 text-sm transition-all ${
                  item.active ? 'bg-coral text-white' : 'text-white/60 hover:bg-white/8 hover:text-white'
                }`}>
                <item.icon size={16} />
                {item.label}
              </div>
            ))}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-white/10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-7 h-7 rounded-full bg-lavender flex items-center justify-center text-xs font-medium">S</div>
          <div>
            <p className="text-xs font-medium text-white">Shreya</p>
            <p className="text-xs text-white/40">July 2026</p>
          </div>
        </div>
        <button onClick={onLogout}
          className="flex items-center gap-2 text-xs text-white/40 hover:text-red-400 transition-colors w-full">
          <LogOut size={13} /> Log out
        </button>
      </div>
    </div>
  );
}