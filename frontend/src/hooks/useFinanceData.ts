import { useState, useEffect, useCallback } from "react";
import API from "../api";

export interface FinanceData {
  budget: any;
  transactions: any[];
  safeToSpend: any;
  forecast: any;
  health: any;
  categories: Record<string, number>;
  loading: boolean; // only true on FIRST load
  refreshing: boolean; // true on background refreshes
  error: string | null;
  refetch: () => void;
}

export function useFinanceData(): FinanceData {
  const [budget, setBudget] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [safeToSpend, setSafeToSpend] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [health, setHealth] = useState(null);
  const [categories, setCategories] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  const fetchAll = useCallback(
    async (isBackground = false) => {
      // On first load — show full loading screen
      // On background refresh — only set refreshing (no loading screen)
      if (!isBackground || !initialized) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      setError(null);

      try {
        const [bRes, tRes, sRes, fRes, hRes] = await Promise.allSettled([
          API.get("/budget/current"),
          API.get("/transactions/"),
          API.get("/calculate/safe-to-spend"),
          API.get("/calculate/forecast"),
          API.get("/agent/health-check"),
        ]);

        if (bRes.status === "fulfilled") setBudget(bRes.value.data);
        if (tRes.status === "fulfilled") {
          setTransactions(tRes.value.data.transactions || []);
          setCategories(tRes.value.data.summary?.by_category || {});
        }
        if (sRes.status === "fulfilled") setSafeToSpend(sRes.value.data);
        if (fRes.status === "fulfilled") setForecast(fRes.value.data);
        if (hRes.status === "fulfilled") setHealth(hRes.value.data);

        setInitialized(true);
      } catch {
        setError("Failed to load data");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [initialized],
  );

  // Initial load
  useEffect(() => {
    fetchAll(false);
  }, [fetchAll]);

  // refetch is always background — never shows loading screen
  const refetch = useCallback(() => {
    fetchAll(true);
  }, [fetchAll]);

  return {
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
  };
}
