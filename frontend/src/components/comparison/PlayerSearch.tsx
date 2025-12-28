import { useMemo, useState } from "react";
import { Player } from "@/types/player";
import { TeamLogo } from "../TeamLogo";
import { cn } from "@/lib/utils";

interface PlayerSearchProps {
  players: Player[];
  onSelect: (player: Player) => void;
  excludeId?: string;
  placeholder?: string;
  filterPosition?: string;
}

export function PlayerSearch({
  players,
  onSelect,
  excludeId,
  filterPosition,
  placeholder = "Search players…",
}: PlayerSearchProps) {
  const [query, setQuery] = useState("");

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = players.filter((p) => {
      if (excludeId && p.player_id === excludeId) return false;
      if (filterPosition && (p.position || "").toUpperCase() !== filterPosition.toUpperCase()) return false;
      if (!q) return true;
      return p.player_name.toLowerCase().includes(q);
    });
    return filtered.slice(0, 60);
  }, [players, query, excludeId, filterPosition]);

  return (
    <div className="space-y-3">
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
        className="w-full h-11 px-3 rounded-lg border border-border bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      />

      <div className="max-h-80 overflow-y-auto pr-1 space-y-2">
        {results.length === 0 ? (
          <p className="text-sm text-muted-foreground px-1">No matches yet.</p>
        ) : (
          results.map((p) => (
            <button
              key={p.player_id}
              type="button"
              onClick={() => onSelect(p)}
              className={cn(
                "w-full rounded-lg border border-transparent bg-secondary/40 hover:bg-secondary/70 transition-colors",
                "flex items-center gap-3 px-3 py-2 text-left"
              )}
            >
              <TeamLogo team={p.team} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground truncate">{p.player_name}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {p.team || "FA"} • {p.position || "—"}
                </p>
              </div>
              <span className="text-xs text-muted-foreground font-mono">{p.seasonTotals?.games ?? p.games ?? "—"}g</span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}


