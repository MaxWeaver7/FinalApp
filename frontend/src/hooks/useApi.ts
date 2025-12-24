import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Player, FilterOptions, PlayerGameLog } from '@/types/player';

const API_BASE = '/api';

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export function useFilterOptions() {
  return useQuery({
    queryKey: ['options'],
    queryFn: () => fetchJson<FilterOptions>(`${API_BASE}/options`),
    staleTime: 1000 * 60 * 10,
  });
}

type PlayersResponse = { players: Player[]; nextOffset?: number; hasMore?: boolean };

export function usePlayers(
  season?: number,
  position?: string,
  team?: string,
  q?: string,
  offset: number = 0,
  limit: number = 250
) {
  const params = new URLSearchParams();
  if (season) params.set('season', season.toString());
  if (position) params.set('position', position);
  if (team) params.set('team', team);
  if (q && q.trim().length >= 2) params.set('q', q.trim());
  params.set('offset', String(Math.max(offset || 0, 0)));
  params.set('limit', String(Math.max(limit || 0, 1)));
  
  return useQuery({
    queryKey: ['players', season, position, team, q || '', offset, limit],
    queryFn: () => fetchJson<PlayersResponse>(`${API_BASE}/players?${params.toString()}`),
    enabled: !!season,
    placeholderData: keepPreviousData,
    staleTime: 1000 * 10,
  });
}

export function usePlayerDetail(playerId: string, season: number) {
  return useQuery({
    queryKey: ['player', playerId, season],
    queryFn: () => fetchJson<{ player: Player; gameLogs: PlayerGameLog[] }>(`${API_BASE}/player/${playerId}?season=${season}`),
    enabled: !!playerId && !!season,
  });
}

export function useSummary() {
  return useQuery({
    queryKey: ['summary'],
    queryFn: () => fetchJson<any>(`${API_BASE}/summary`),
  });
}


