import { createContext, useContext, useMemo, type ReactNode, useCallback, useEffect, useState } from "react";
import { api } from "@/api/services";
import type { CommonParams } from "@/api/client";
import { chinaDate, deviceId, marketSessionDate } from "@/lib/format";

type Settings = {
  token: string;
  userId: string;
};

type AppState = {
  date: string;
  today: string;
  holidays: Set<string>;
  settings: Settings;
  common: CommonParams;
  setDate: (date: string) => void;
  saveSettings: (next: Settings) => void;
  isToday: boolean;
  refresh: () => void;
};

const AppCtx = createContext<AppState | null>(null);

const SETTINGS_KEY = "kpl.settings";

function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return { token: "", userId: "" };
    const parsed = JSON.parse(raw) as Settings;
    return { token: parsed.token || "", userId: parsed.userId || "" };
  } catch {
    return { token: "", userId: "" };
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const today = chinaDate();
  const [date, setDateState] = useState(() => marketSessionDate(new Set()));
  const [settings, setSettings] = useState<Settings>(() => loadSettings());
  const [holidays, setHolidays] = useState<Set<string>>(new Set());
  const [tick, setTick] = useState(0);

  const common = useMemo<CommonParams>(() => {
    const next: CommonParams = {
      DeviceID: deviceId(),
      PhoneOSNew: "2",
      VerSion: "5.23.0.1",
      apiv: "w44",
    };
    if (settings.token) next.Token = settings.token;
    if (settings.userId) next.UserID = settings.userId;
    return next;
  }, [settings, tick]);

  useEffect(() => {
    api
      .holidays({
        DeviceID: deviceId(),
        PhoneOSNew: "2",
        VerSion: "5.23.0.1",
        apiv: "w44",
      })
      .then((res) => {
        const set = new Set(res.List || []);
        setHolidays(set);
        setDateState((current) => (current === chinaDate() ? marketSessionDate(set) : current));
      })
      .catch(() => {
        /* ignore holiday fetch failure */
      });
  }, []);

  const setDate = useCallback((next: string) => {
    setDateState(next);
  }, []);

  const saveSettings = useCallback((next: Settings) => {
    setSettings(next);
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(next));
  }, []);

  const value = useMemo<AppState>(
    () => ({
      date,
      today,
      holidays,
      settings,
      common,
      setDate,
      saveSettings,
      isToday: date === today,
      refresh: () => setTick((n) => n + 1),
    }),
    [date, today, holidays, settings, common, setDate, saveSettings],
  );

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}

export function useApp() {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
