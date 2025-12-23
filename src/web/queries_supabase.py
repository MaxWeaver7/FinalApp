from __future__ import annotations

import re
from typing import Any, Optional

from src.database.supabase_client import SupabaseClient


def player_photo_url(player_id: str) -> Optional[str]:
    # Deprecated signature (kept for compatibility). Use player_photo_url_from_name_team instead.
    return None


_NAME_RE = re.compile(r"[^a-z0-9 ]+")


def _merge_name(name: str) -> str:
    s = _NAME_RE.sub("", (name or "").lower()).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def player_photo_url_from_name_team(*, name: str, team: Optional[str]) -> Optional[str]:
    """
    Best-effort headshot URL based on player name + team.

    Uses dynastyprocess db_playerids.csv (already cached in hrb/data/db_playerids.csv).
    Prefers ESPN headshots, falls back to Sleeper.
    """
    # Lazy import to avoid pandas dependency on cold paths if unused.
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return None

    from functools import lru_cache
    from pathlib import Path

    @lru_cache(maxsize=1)
    def _df():
        repo_root = Path(__file__).resolve().parents[2]  # hrb/
        path = repo_root / "data" / "db_playerids.csv"
        if not path.exists():
            return None
        try:
            return pd.read_csv(path, dtype=str)
        except Exception:
            return None

    df = _df()
    if df is None or df is not None and getattr(df, "empty", False):
        return None
    if "merge_name" not in df.columns or "team" not in df.columns:
        return None

    mn = _merge_name(name)
    if not mn:
        return None

    team_abbr = (team or "").strip().upper()
    sub = df[df["merge_name"] == mn]
    if sub.empty:
        return None
    if team_abbr:
        tsub = sub[sub["team"].fillna("").str.upper() == team_abbr]
        if not tsub.empty:
            sub = tsub
    # Prefer latest season row if present.
    if "db_season" in sub.columns:
        try:
            sub = sub.assign(_season=pd.to_numeric(sub["db_season"], errors="coerce")).sort_values("_season", ascending=False)
        except Exception:
            pass
    rec = sub.iloc[0].to_dict()
    espn_id = str(rec.get("espn_id") or "").strip()
    sleeper_id = str(rec.get("sleeper_id") or "").strip()
    if espn_id and espn_id.lower() != "nan":
        return f"https://a.espncdn.com/i/headshots/nfl/players/full/{espn_id}.png"
    if sleeper_id and sleeper_id.lower() != "nan":
        return f"https://sleepercdn.com/content/nfl/players/{sleeper_id}.jpg"
    return None


def _uniq_sorted_int(vals: list[Any], *, desc: bool = False) -> list[int]:
    out: list[int] = []
    seen = set()
    for v in vals:
        try:
            i = int(v)
        except Exception:
            continue
        if i in seen:
            continue
        seen.add(i)
        out.append(i)
    return sorted(out, reverse=desc)


def _in_list(values: list[int]) -> str:
    inner = ",".join(str(int(v)) for v in values)
    return f"in.({inner})"

def _safe_int(x: Any) -> Optional[int]:
    try:
        if x is None or x == "":
            return None
        return int(x)
    except Exception:
        return None


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _team_map(sb: SupabaseClient, team_ids: list[int]) -> dict[int, str]:
    team_map: dict[int, str] = {}
    if not team_ids:
        return team_map
    teams = sb.select("nfl_teams", select="id,abbreviation", filters={"id": _in_list(team_ids)}, limit=len(team_ids))
    for t in teams:
        try:
            team_map[int(t["id"])] = str(t.get("abbreviation") or "").upper()
        except Exception:
            continue
    return team_map


def options(sb: SupabaseClient) -> dict[str, Any]:
    games = sb.select("nfl_games", select="season,week", order="season.desc,week.asc", limit=5000)
    seasons = _uniq_sorted_int([g.get("season") for g in games], desc=True)
    weeks = _uniq_sorted_int([g.get("week") for g in games], desc=False)
    teams = sb.select("nfl_teams", select="abbreviation", order="abbreviation.asc", limit=1000)
    team_abbr = [t.get("abbreviation") for t in teams if isinstance(t.get("abbreviation"), str)]
    positions = ["QB", "RB", "WR", "TE"]
    return {"seasons": seasons, "weeks": weeks, "teams": team_abbr, "positions": positions}


def summary(sb: SupabaseClient) -> dict[str, Any]:
    games = sb.count("nfl_games")
    players = sb.count("nfl_players")
    teams = sb.count("nfl_teams")
    seasons_rows = sb.select("nfl_games", select="season", order="season.asc", limit=5000)
    seasons = _uniq_sorted_int([r.get("season") for r in seasons_rows], desc=False)
    # Mirror the existing JSON shape expected by the React UI (it doesn't depend on most fields).
    return {"seasons": seasons, "games": games, "players": players, "teams": teams}

def _has_any_stats(row: dict[str, Any]) -> bool:
    # Use a conservative definition: player recorded at least one meaningful stat.
    for k in (
        "passing_attempts",
        "passing_completions",
        "rushing_attempts",
        "receptions",
        "receiving_targets",
    ):
        v = _safe_int(row.get(k))
        if v and v > 0:
            return True
    # Some defensive players could appear with games_played but no tracked offensive stats; keep them out.
    return False


def get_players_list(
    sb: SupabaseClient,
    *,
    season: Optional[int],
    position: Optional[str],
    team: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    # Season stats drive both the displayed totals and the "only players with recorded stats" filter.
    if season is None:
        return []

    # Filter by team abbreviation (best-effort; uses current team on nfl_players).
    team_id: Optional[int] = None
    if team:
        t = sb.select("nfl_teams", select="id", filters={"abbreviation": f"eq.{team}"}, limit=1)
        if t:
            team_id = _safe_int(t[0].get("id"))

    stats_filters: dict[str, Any] = {"season": f"eq.{int(season)}", "postseason": "eq.false"}
    # Pull more than requested; we'll filter down after joining to players and applying position/team.
    stats_rows = sb.select(
        "nfl_player_season_stats",
        select=(
            "player_id,games_played,"
            "passing_attempts,passing_completions,passing_yards,passing_touchdowns,passing_interceptions,"
            "qbr,qb_rating,"
            "rushing_attempts,rushing_yards,rushing_touchdowns,"
            "receptions,receiving_yards,receiving_touchdowns,receiving_targets"
        ),
        filters=stats_filters,
        limit=8000,
    )
    stats_rows = [r for r in stats_rows if _has_any_stats(r)]
    if not stats_rows:
        return []

    player_ids = [_safe_int(r.get("player_id")) for r in stats_rows]
    player_ids = [pid for pid in player_ids if pid is not None]
    if not player_ids:
        return []

    players = sb.select(
        "nfl_players",
        select="id,first_name,last_name,position_abbreviation,team_id",
        filters={"id": _in_list(player_ids)},
        limit=len(player_ids),
    )
    player_map: dict[int, dict[str, Any]] = {}
    for p in players:
        pid = _safe_int(p.get("id"))
        if pid is None:
            continue
        player_map[pid] = p

    # Team abbreviation map (current team on player record).
    team_ids = sorted({int(p["team_id"]) for p in players if p.get("team_id") not in (None, "")})
    team_map = _team_map(sb, team_ids)

    pos_filter = (position or "").strip().upper()
    out: list[dict[str, Any]] = []
    for s in stats_rows:
        pid = _safe_int(s.get("player_id"))
        if pid is None:
            continue
        p = player_map.get(pid)
        if not p:
            continue
        pos = (p.get("position_abbreviation") or "").strip().upper()
        if pos_filter and pos != pos_filter:
            continue

        tid = _safe_int(p.get("team_id"))
        if team_id is not None and tid != team_id:
            continue

        first = (p.get("first_name") or "").strip()
        last = (p.get("last_name") or "").strip()
        name = (first + " " + last).strip() or str(pid)
        team_abbr = team_map.get(tid) if tid is not None else None

        games = _safe_int(s.get("games_played")) or 0
        targets = _safe_int(s.get("receiving_targets")) or 0
        rec = _safe_int(s.get("receptions")) or 0
        rec_yards = _safe_int(s.get("receiving_yards")) or 0
        rec_tds = _safe_int(s.get("receiving_touchdowns")) or 0
        rush_att = _safe_int(s.get("rushing_attempts")) or 0
        rush_yards = _safe_int(s.get("rushing_yards")) or 0
        rush_tds = _safe_int(s.get("rushing_touchdowns")) or 0
        pass_att = _safe_int(s.get("passing_attempts")) or 0
        pass_cmp = _safe_int(s.get("passing_completions")) or 0
        pass_yds = _safe_int(s.get("passing_yards")) or 0
        pass_tds = _safe_int(s.get("passing_touchdowns")) or 0
        pass_int = _safe_int(s.get("passing_interceptions")) or 0
        qb_rating = _safe_float(s.get("qb_rating"))
        qbr = _safe_float(s.get("qbr"))

        avg_ypc = (float(rec_yards) / float(rec)) if rec else 0.0
        avg_ypr = (float(rush_yards) / float(rush_att)) if rush_att else 0.0
        photo = player_photo_url_from_name_team(name=name, team=team_abbr)

        out.append(
            {
                "player_id": str(pid),
                "player_name": name,
                "team": team_abbr,
                "position": pos or None,
                "season": season,
                "games": games,
                "targets": targets,
                "receptions": rec,
                "receivingYards": rec_yards,
                "receivingTouchdowns": rec_tds,
                "avgYardsPerCatch": avg_ypc,
                "rushAttempts": rush_att,
                "rushingYards": rush_yards,
                "rushingTouchdowns": rush_tds,
                "avgYardsPerRush": avg_ypr,
                "passingAttempts": pass_att,
                "passingCompletions": pass_cmp,
                "passingYards": pass_yds,
                "passingTouchdowns": pass_tds,
                "passingInterceptions": pass_int,
                "qbRating": qb_rating,
                "qbr": qbr,
                "photoUrl": photo,
            }
        )

    # Sort: receivers by receiving yards, rushers/QBs by rushing yards (simple, UX-friendly).
    def sort_key(r: dict[str, Any]) -> int:
        pos = (r.get("position") or "").upper()
        if pos in {"WR", "TE"}:
            return int(r.get("receivingYards") or 0)
        return int(r.get("rushingYards") or 0)

    out.sort(key=sort_key, reverse=True)
    return out[: min(max(limit, 1), 300)]


def get_player_game_logs(
    sb: SupabaseClient,
    player_id: str,
    season: int,
    *,
    include_postseason: bool = False,
) -> list[dict[str, Any]]:
    pid = _safe_int(player_id)
    if pid is None:
        return []

    # If include_postseason, return both; otherwise regular season only.
    filters: dict[str, Any] = {
        "player_id": f"eq.{pid}",
        "season": f"eq.{int(season)}",
    }
    if not include_postseason:
        filters["postseason"] = "eq.false"

    rows = sb.select(
        "nfl_player_game_stats",
        select=(
            "player_id,game_id,season,week,postseason,team_id,"
            "rushing_attempts,rushing_yards,rushing_touchdowns,"
            "receptions,receiving_yards,receiving_touchdowns,receiving_targets,"
            "passing_attempts,passing_completions,passing_yards,passing_touchdowns,passing_interceptions,"
            "qbr,qb_rating"
        ),
        filters=filters,
        order="week.asc",
        limit=400,
    )
    if not rows:
        return []

    game_ids = sorted({int(r["game_id"]) for r in rows if r.get("game_id") not in (None, "")})
    games = sb.select(
        "nfl_games",
        select="id,home_team_id,visitor_team_id,postseason",
        filters={"id": _in_list(game_ids)},
        limit=len(game_ids),
    )
    game_map: dict[int, dict[str, Any]] = {}
    team_ids = set()
    for g in games:
        gid = _safe_int(g.get("id"))
        if gid is None:
            continue
        game_map[gid] = g
        ht = _safe_int(g.get("home_team_id"))
        vt = _safe_int(g.get("visitor_team_id"))
        if ht is not None:
            team_ids.add(ht)
        if vt is not None:
            team_ids.add(vt)

    # Also include player's team_id values for mapping to abbreviation.
    for r in rows:
        tid = _safe_int(r.get("team_id"))
        if tid is not None:
            team_ids.add(tid)

    tmap = _team_map(sb, sorted(team_ids))

    out: list[dict[str, Any]] = []
    for r in rows:
        gid = _safe_int(r.get("game_id"))
        if gid is None:
            continue
        g = game_map.get(gid, {})
        ht = _safe_int(g.get("home_team_id"))
        vt = _safe_int(g.get("visitor_team_id"))
        tid = _safe_int(r.get("team_id"))

        team_abbr = tmap.get(tid) if tid is not None else None
        home_abbr = tmap.get(ht) if ht is not None else None
        away_abbr = tmap.get(vt) if vt is not None else None

        location = "home"
        opp = None
        if tid is not None and ht is not None and vt is not None:
            if tid == ht:
                location = "home"
                opp = away_abbr
            else:
                location = "away"
                opp = home_abbr

        out.append(
            {
                "season": _safe_int(r.get("season")) or season,
                "week": _safe_int(r.get("week")) or 0,
                "game_id": str(gid),
                "team": team_abbr,
                "opponent": opp,
                "home_team": home_abbr,
                "away_team": away_abbr,
                "location": location,
                "is_postseason": bool(r.get("postseason")),
                # Receiving
                "targets": _safe_int(r.get("receiving_targets")) or 0,
                "receptions": _safe_int(r.get("receptions")) or 0,
                "rec_yards": _safe_int(r.get("receiving_yards")) or 0,
                "rec_tds": _safe_int(r.get("receiving_touchdowns")) or 0,
                "air_yards": 0,
                "yac": 0,
                # no EPA yet
                # Rushing
                "rush_attempts": _safe_int(r.get("rushing_attempts")) or 0,
                "rush_yards": _safe_int(r.get("rushing_yards")) or 0,
                "rush_tds": _safe_int(r.get("rushing_touchdowns")) or 0,
                # Passing
                "passing_attempts": _safe_int(r.get("passing_attempts")) or 0,
                "passing_completions": _safe_int(r.get("passing_completions")) or 0,
                "passing_yards": _safe_int(r.get("passing_yards")) or 0,
                "passing_tds": _safe_int(r.get("passing_touchdowns")) or 0,
                "interceptions": _safe_int(r.get("passing_interceptions")) or 0,
                "qb_rating": _safe_float(r.get("qb_rating")),
                "qbr": _safe_float(r.get("qbr")),
            }
        )

    return out


def receiving_dashboard(
    sb: SupabaseClient,
    *,
    season: int,
    week: int,
    team: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    # Pull weekly player game stats, then hydrate player + team display fields.
    filters: dict[str, Any] = {"season": f"eq.{int(season)}", "week": f"eq.{int(week)}", "postseason": "eq.false"}
    if team:
        t = sb.select("nfl_teams", select="id", filters={"abbreviation": f"eq.{team}"}, limit=1)
        tid = _safe_int(t[0].get("id")) if t else None
        if tid is not None:
            filters["team_id"] = f"eq.{tid}"
    stats = sb.select(
        "nfl_player_game_stats",
        select="player_id,team_id,season,week,receiving_targets,receptions,receiving_yards,receiving_touchdowns",
        filters=filters,
        limit=5000,
    )
    # sort client-side
    stats.sort(key=lambda r: _safe_int(r.get("receiving_targets")) or 0, reverse=True)
    stats = stats[: min(max(limit, 1), 200)]

    pids = sorted({_safe_int(r.get("player_id")) for r in stats if _safe_int(r.get("player_id")) is not None})
    players = sb.select("nfl_players", select="id,first_name,last_name,position_abbreviation", filters={"id": _in_list(pids)}, limit=len(pids))
    pmap = {int(p["id"]): p for p in players if _safe_int(p.get("id")) is not None}

    team_ids = sorted({_safe_int(r.get("team_id")) for r in stats if _safe_int(r.get("team_id")) is not None})
    tmap = _team_map(sb, [t for t in team_ids if t is not None])

    out = []
    for r in stats:
        pid = _safe_int(r.get("player_id"))
        if pid is None:
            continue
        p = pmap.get(pid, {})
        name = (str(p.get("first_name") or "").strip() + " " + str(p.get("last_name") or "").strip()).strip() or str(pid)
        tid = _safe_int(r.get("team_id"))
        out.append(
            {
                "season": season,
                "week": week,
                "team": tmap.get(tid) if tid is not None else None,
                "player_id": str(pid),
                "player_name": name,
                "position": (p.get("position_abbreviation") or None),
                "targets": _safe_int(r.get("receiving_targets")) or 0,
                "receptions": _safe_int(r.get("receptions")) or 0,
                "rec_yards": _safe_int(r.get("receiving_yards")) or 0,
                "rec_tds": _safe_int(r.get("receiving_touchdowns")) or 0,
                "air_yards": 0,
                "yac": 0,
                "photoUrl": player_photo_url_from_name_team(name=name, team=tmap.get(tid) if tid is not None else None),
            }
        )
    return out


def rushing_dashboard(
    sb: SupabaseClient,
    *,
    season: int,
    week: int,
    team: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    filters: dict[str, Any] = {"season": f"eq.{int(season)}", "week": f"eq.{int(week)}", "postseason": "eq.false"}
    if team:
        t = sb.select("nfl_teams", select="id", filters={"abbreviation": f"eq.{team}"}, limit=1)
        tid = _safe_int(t[0].get("id")) if t else None
        if tid is not None:
            filters["team_id"] = f"eq.{tid}"
    stats = sb.select(
        "nfl_player_game_stats",
        select="player_id,team_id,season,week,rushing_attempts,rushing_yards,rushing_touchdowns,receptions,receiving_yards",
        filters=filters,
        limit=5000,
    )
    stats.sort(key=lambda r: _safe_int(r.get("rushing_yards")) or 0, reverse=True)
    stats = stats[: min(max(limit, 1), 200)]

    pids = sorted({_safe_int(r.get("player_id")) for r in stats if _safe_int(r.get("player_id")) is not None})
    players = sb.select("nfl_players", select="id,first_name,last_name,position_abbreviation", filters={"id": _in_list(pids)}, limit=len(pids))
    pmap = {int(p["id"]): p for p in players if _safe_int(p.get("id")) is not None}
    team_ids = sorted({_safe_int(r.get("team_id")) for r in stats if _safe_int(r.get("team_id")) is not None})
    tmap = _team_map(sb, [t for t in team_ids if t is not None])

    out = []
    for r in stats:
        pid = _safe_int(r.get("player_id"))
        if pid is None:
            continue
        p = pmap.get(pid, {})
        name = (str(p.get("first_name") or "").strip() + " " + str(p.get("last_name") or "").strip()).strip() or str(pid)
        tid = _safe_int(r.get("team_id"))
        out.append(
            {
                "season": season,
                "week": week,
                "team": tmap.get(tid) if tid is not None else None,
                "player_id": str(pid),
                "player_name": name,
                "position": (p.get("position_abbreviation") or None),
                "rush_attempts": _safe_int(r.get("rushing_attempts")) or 0,
                "rush_yards": _safe_int(r.get("rushing_yards")) or 0,
                "rush_tds": _safe_int(r.get("rushing_touchdowns")) or 0,
                "receptions": _safe_int(r.get("receptions")) or 0,
                "rec_yards": _safe_int(r.get("receiving_yards")) or 0,
                "photoUrl": player_photo_url_from_name_team(name=name, team=tmap.get(tid) if tid is not None else None),
            }
        )
    return out


def receiving_season(
    sb: SupabaseClient,
    *,
    season: int,
    team: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    # Use season stats; team is best-effort (current team).
    rows = get_players_list(sb, season=season, position=None, team=team, limit=8000)
    # compute team target share within returned team scope
    by_team: dict[str, int] = {}
    for r in rows:
        t = r.get("team") or ""
        by_team[t] = by_team.get(t, 0) + int(r.get("targets") or 0)
    out = []
    for r in rows:
        pos = (r.get("position") or "").upper()
        if pos not in {"WR", "TE", "RB"}:
            continue
        t = r.get("team") or ""
        denom = by_team.get(t, 0) or 0
        share = (float(r.get("targets") or 0) / float(denom)) if denom else None
        out.append(
            {
                "season": season,
                "team": r.get("team"),
                "player_id": r.get("player_id"),
                "player_name": r.get("player_name"),
                "position": r.get("position"),
                "targets": int(r.get("targets") or 0),
                "receptions": int(r.get("receptions") or 0),
                "rec_yards": int(r.get("receivingYards") or 0),
                "air_yards": 0,
                "rec_tds": int(r.get("receivingTouchdowns") or 0),
                "team_target_share": share,
                "photoUrl": player_photo_url_from_name_team(name=str(r.get("player_name") or ""), team=str(r.get("team") or "")),
            }
        )
    out.sort(key=lambda x: int(x.get("targets") or 0), reverse=True)
    return out[: min(max(limit, 1), 200)]


def rushing_season(
    sb: SupabaseClient,
    *,
    season: int,
    team: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    rows = get_players_list(sb, season=season, position=None, team=team, limit=8000)
    by_team: dict[str, int] = {}
    for r in rows:
        t = r.get("team") or ""
        by_team[t] = by_team.get(t, 0) + int(r.get("rushAttempts") or 0)
    out = []
    for r in rows:
        pos = (r.get("position") or "").upper()
        if pos not in {"RB", "QB", "WR", "TE"}:
            continue
        t = r.get("team") or ""
        denom = by_team.get(t, 0) or 0
        share = (float(r.get("rushAttempts") or 0) / float(denom)) if denom else None
        out.append(
            {
                "season": season,
                "team": r.get("team"),
                "player_id": r.get("player_id"),
                "player_name": r.get("player_name"),
                "position": r.get("position"),
                "rush_attempts": int(r.get("rushAttempts") or 0),
                "rush_yards": int(r.get("rushingYards") or 0),
                "rush_tds": int(r.get("rushingTouchdowns") or 0),
                "team_rush_share": share,
                "photoUrl": player_photo_url_from_name_team(name=str(r.get("player_name") or ""), team=str(r.get("team") or "")),
            }
        )
    out.sort(key=lambda x: int(x.get("rush_yards") or 0), reverse=True)
    return out[: min(max(limit, 1), 200)]


