import axios from "axios";
import { Target, CheckRecord, Stats } from "../types";

const BASE = "http://localhost:8000";

export const getHealth = async () => {
  const r = await axios.get(`${BASE}/health`);
  return r.data;
};

export const createTarget = async (url: string) => {
  const r = await axios.post(`${BASE}/targets`, { url });
  return r.data as Target;
};

export const getTargets = async (): Promise<Target[]> => {
  const r = await axios.get(`${BASE}/targets`);
  return r.data as Target[];
};

export const deleteTarget = async (id: string) => {
  await axios.delete(`${BASE}/targets/${id}`);
};

export const checkNow = async (id: string) => {
  const r = await axios.post(`${BASE}/targets/${id}/check`);
  return r.data;
};

export const getHistory = async (id: string): Promise<CheckRecord[]> => {
  const r = await axios.get(`${BASE}/targets/${id}/history`);
  return r.data.checks as CheckRecord[];
};

export const getStats = async (id: string): Promise<Stats> => {
  const r = await axios.get(`${BASE}/targets/${id}/stats`);

  return {
    uptime_24h: r.data.uptime_percentage,
    average_response_time_ms: r.data.average_response_time_ms,
    current_status: r.data.current_status,
    last_checked_at: r.data.last_checked_at,
  };
};