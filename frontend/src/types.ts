export interface Target {
  id: string;
  url: string;
  created_at?: string;
  last_checked_at?: string | null;
  online?: boolean;
  last_status_code?: number | null;
  average_response_time_ms?: number | null;
  uptime_24h?: number | null; // percentage 0-100
}

export interface CheckRecord {
  id: string;
  checked_at: string; // ISO
  response_time_ms?: number | null;
  status_code?: number | null;
  error?: string | null;
}

export interface Stats {
  uptime_24h?: number | null;
  average_response_time_ms?: number | null;
  current_status?: boolean;
  last_checked_at?: string | null;
}
