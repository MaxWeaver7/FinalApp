import { useMemo, useState, useEffect } from "react";
import { cn, formatStat } from "@/lib/utils";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { GoatAdvancedPayload, GoatAdvancedRow } from "@/types/player";

interface GoatAdvancedStatsProps {
  data?: GoatAdvancedPayload | null;
  className?: string;
}

type Kind = "receiving" | "rushing" | "passing";

export function GoatAdvancedStats({ data, className }: GoatAdvancedStatsProps) {
  // Determine which stat types have data
  const availableKinds = useMemo(() => {
    const kinds: Kind[] = [];
    if (data?.regular?.passing?.length) kinds.push("passing");
    if (data?.regular?.rushing?.length) kinds.push("rushing");
    if (data?.regular?.receiving?.length) kinds.push("receiving");
    return kinds;
  }, [data]);

  // Auto-select first available kind
  const [kind, setKind] = useState<Kind>(availableKinds[0] || "receiving");

  // Update kind if data changes and current kind has no data
  useEffect(() => {
    if (availableKinds.length > 0 && !availableKinds.includes(kind)) {
      setKind(availableKinds[0]);
    }
  }, [availableKinds, kind]);

  const rows = useMemo(() => {
    const r = data?.regular?.[kind] || [];
    return Array.isArray(r) ? r : [];
  }, [data, kind]);

  const columns = useMemo(() => {
    if (kind === "receiving") {
      return [
        { k: "week", label: "WK", type: "int" as const },
        { k: "targets", label: "TGT", type: "int" as const },
        { k: "receptions", label: "REC", type: "int" as const },
        { k: "yards", label: "YDS", type: "int" as const },
        { k: "avg_intended_air_yards", label: "aIAY", type: "float" as const },
        { k: "avg_yac", label: "aYAC", type: "float" as const },
        { k: "avg_separation", label: "SEP", type: "float" as const },
        { k: "avg_cushion", label: "CUSH", type: "float" as const },
        { k: "catch_percentage", label: "CATCH%", type: "float" as const },
        { k: "rec_touchdowns", label: "TD", type: "int" as const },
      ];
    }
    if (kind === "rushing") {
      return [
        { k: "week", label: "WK", type: "int" as const },
        { k: "rush_attempts", label: "ATT", type: "int" as const },
        { k: "rush_yards", label: "YDS", type: "int" as const },
        { k: "rush_touchdowns", label: "TD", type: "int" as const },
        { k: "avg_time_to_los", label: "TTLOS", type: "float" as const },
        { k: "expected_rush_yards", label: "xRushY", type: "float" as const },
        { k: "rush_yards_over_expected", label: "RYOE", type: "float" as const },
        { k: "efficiency", label: "EFF", type: "float" as const },
        { k: "avg_rush_yards", label: "AVG", type: "float" as const },
      ];
    }
    return [
      { k: "week", label: "WK", type: "int" as const },
      { k: "attempts", label: "ATT", type: "int" as const },
      { k: "completions", label: "COMP", type: "int" as const },
      { k: "pass_yards", label: "YDS", type: "int" as const },
      { k: "pass_touchdowns", label: "TD", type: "int" as const },
      { k: "interceptions", label: "INT", type: "int" as const },
      { k: "passer_rating", label: "RATE", type: "float" as const },
      { k: "completion_percentage", label: "COMP%", type: "float" as const },
      { k: "avg_time_to_throw", label: "TTT", type: "float" as const },
      { k: "avg_intended_air_yards", label: "IAY", type: "float" as const },
      { k: "aggressiveness", label: "AGG", type: "float" as const },
    ];
  }, [kind]);

  const fmt = (colType: "int" | "float", v: any, colKey?: string) => {
    // Special handling for week column
    if (colKey === "week") {
      const weekNum = v ?? 0;
      if (weekNum === 0) return "TOTAL";
      return String(weekNum);
    }
    if (colType === "int") return formatStat(v ?? 0, { integer: true });
    // Percent-like columns should still be X.XX (we can add % sign later once we confirm units).
    return formatStat(v);
  };

  return (
    <div className={cn("glass-card rounded-xl overflow-hidden", className)}>
      <div className="p-4 border-b border-border flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-foreground">GOAT Advanced Stats</h3>
          <p className="text-sm text-muted-foreground">Weekly + season totals</p>
        </div>
        <div className="flex items-center gap-2">
          {availableKinds.map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setKind(k)}
              className={cn(
                "h-9 px-3 rounded-lg border border-border text-sm transition-colors",
                k === kind ? "bg-secondary text-foreground" : "bg-transparent text-muted-foreground hover:bg-secondary"
              )}
              aria-pressed={k === kind}
            >
              {k[0].toUpperCase() + k.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              {columns.map((c) => (
                <TableHead key={c.k} className="text-muted-foreground font-medium text-center">
                  {c.label}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow className="border-border">
                <TableCell colSpan={columns.length} className="text-muted-foreground text-center py-8">
                  No GOAT advanced rows for this player/season yet.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((r: GoatAdvancedRow, idx: number) => (
                <TableRow key={idx} className="data-row border-border">
                  {columns.map((c) => (
                    <TableCell key={c.k} className="text-center font-mono">
                      {fmt(c.type, r[c.k], c.k)}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}


