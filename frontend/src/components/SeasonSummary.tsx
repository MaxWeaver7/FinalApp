import { Player } from "@/types/player";
import { StatCard } from "./StatCard";
import { cn, formatStat, getStatTrend } from "@/lib/utils";
import { TeamLogo } from "./TeamLogo";
import { useState } from "react";

interface SeasonSummaryProps {
  player: Player;
}

export function SeasonSummary({ player }: SeasonSummaryProps) {
  const stats = player.seasonTotals || player;
  const isReceiver = ['WR', 'TE'].includes(player.position || '');
  const isQB = (player.position || '').toUpperCase() === 'QB';
  const photoUrl = player.photoUrl;
  const [imgError, setImgError] = useState(false);
  const showImage = !!photoUrl && !imgError;
  const accent = player.teamColors?.primary || "";

  const chips: string[] = [];
  if (player.jersey_number) chips.push(`#${player.jersey_number}`);
  const hw = [player.height, player.weight].filter(Boolean).join(" / ");
  if (hw) chips.push(hw);
  if (typeof player.age === "number") chips.push(`Age ${player.age}`);
  if (player.experience) chips.push(`Exp ${player.experience}`);
  if (player.college) chips.push(player.college);
  
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 opacity-0 animate-slide-up" style={{ animationDelay: '100ms' }}>
        <div className="w-20 h-20 rounded-2xl bg-secondary overflow-hidden ring-2 ring-border">
          {showImage ? (
            <img
              src={photoUrl}
              alt={player.player_name}
              className="w-full h-full object-cover"
              loading="lazy"
              onError={() => {
                setImgError(true);
              }}
            />
          ) : null}
          <div className={cn(
            "w-full h-full flex items-center justify-center text-muted-foreground text-2xl font-bold",
            showImage && "hidden"
          )}>
            {player.player_name.split(' ').map(n => n[0]).join('')}
          </div>
        </div>
        <div>
          <h2 className="text-2xl font-bold text-foreground">{player.player_name}</h2>
          <div className="flex items-center gap-2 text-muted-foreground">
            <TeamLogo team={player.team} size="md" />
            <p>{player.team} • {player.position} • {stats.season || player.season} Season</p>
          </div>
          {chips.length ? (
            <div className="flex flex-wrap gap-2 mt-3">
              {chips.map((c) => (
                <span
                  key={c}
                  className="px-3 py-1 rounded-full text-xs font-mono text-muted-foreground border bg-secondary/20"
                  style={{ borderColor: accent || undefined }}
                >
                  {c}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {isQB ? (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatCard 
            label="Pass Yards" 
            value={stats.passingYards || 0} 
            subValue={`${stats.games || 0} games`}
            trend={getStatTrend('passing yards', stats.passingYards || 0)}
            delay={150}
          />
          <StatCard 
            label="Pass TDs" 
            value={stats.passingTouchdowns || 0} 
            subValue="Passing"
            trend={getStatTrend('touchdown', stats.passingTouchdowns || 0)}
            delay={200}
          />
          <StatCard 
            label="Rush Yards" 
            value={stats.rushingYards || 0} 
            subValue={`${formatStat(stats.avgYardsPerRush || 0)} avg`}
            trend={getStatTrend('rushingYards', stats.rushingYards || 0)}
            delay={250}
          />
          <StatCard 
            label="Rush TDs" 
            value={stats.rushingTouchdowns || 0} 
            subValue="Rushing"
            trend={getStatTrend('touchdown', stats.rushingTouchdowns || 0)}
            delay={300}
          />
          <StatCard 
            label="INT" 
            value={stats.passingInterceptions || 0} 
            subValue={`${formatStat(stats.qbRating)} rating`}
            delay={350}
          />
        </div>
      ) : isReceiver ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard 
            label="Receptions" 
            value={stats.receptions || 0} 
            subValue={`${stats.games || 0} games`}
            delay={150}
          />
          <StatCard 
            label="Rec Yards" 
            value={stats.receivingYards || 0} 
            subValue={`${formatStat(stats.avgYardsPerCatch || 0)} avg`}
            trend={getStatTrend('receivingYards', stats.receivingYards || 0)}
            delay={200}
          />
          <StatCard 
            label="Targets" 
            value={stats.targets || 0} 
            subValue={`${formatStat((stats.targets || 0) / (stats.games || 1))} per game`}
            delay={250}
          />
          <StatCard 
            label="Rec TDs" 
            value={stats.receivingTouchdowns || 0} 
            subValue="Touchdowns"
            trend={getStatTrend('touchdown', stats.receivingTouchdowns || 0)}
            delay={300}
          />
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard 
            label="Rush Attempts" 
            value={stats.rushAttempts || 0} 
            subValue={`${stats.games || 0} games`}
            delay={150}
          />
          <StatCard 
            label="Rush Yards" 
            value={stats.rushingYards || 0} 
            subValue={`${formatStat(stats.avgYardsPerRush || 0)} avg`}
            trend={getStatTrend('rushingYards', stats.rushingYards || 0)}
            delay={200}
          />
          <StatCard 
            label="Rush TDs" 
            value={stats.rushingTouchdowns || 0} 
            subValue="Touchdowns"
            trend={getStatTrend('touchdown', stats.rushingTouchdowns || 0)}
            delay={250}
          />
          <StatCard 
            label="Receptions" 
            value={stats.receptions || 0} 
            subValue={`${stats.receivingYards || 0} rec yards`}
            delay={300}
          />
        </div>
      )}
    </div>
  );
}

