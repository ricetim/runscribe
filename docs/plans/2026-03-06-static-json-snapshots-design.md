# Design: Static JSON Snapshots for Instant Read Performance

**Date:** 2026-03-06
**Status:** Approved

## Problem

Two distinct performance issues:
1. Every visit: multiple sequential API roundtrips load each dashboard widget separately
2. Morning cold start: 5+ minute wait because all short-lived TTL caches (30s–5min) have expired overnight, triggering simultaneous fresh computation of VDOT, personal bests, training load, and stats on a cold Python process

## Solution: Static JSON Snapshots (Option A)

Reads never touch Python. nginx serves pre-built JSON files directly from disk. FastAPI handles only writes, and after every write it regenerates the affected JSON files in the background.

```
Browser
  │
  ├─ GET /static/*.json  ──→  nginx → /data/static/ (disk, instant)
  │
  └─ POST/PATCH/DELETE /api/  ──→  nginx → FastAPI → SQLite
                                              │
                                              └─ rebuild JSON files → /data/static/
```

The React app, Docker setup, and all UI interactions remain unchanged. Only the data source for reads changes.

## Static File Inventory

All files land in `/data/static/` (existing Docker volume, persists across restarts).

| File | Contents | Rebuilt when |
|------|----------|--------------|
| `activities.json` | Full activity list with metadata | Upload, delete activity, sync |
| `activity-{id}.json` | Activity metadata + laps + analytics | Upload that activity, sync |
| `datapoints-{id}.json` | Raw datapoints for charts/map | Upload that activity |
| `dashboard.json` | Stats summary, training load, VDOT, personal bests | Upload, delete, sync |
| `goals.json` | All goals with computed progress | Any goal write, upload (progress changes) |
| `shoes.json` | All shoes with mileage totals | Any shoe write, upload |
| `plans.json` | All training plans (list) | Any plan write |
| `plan-{id}.json` | Plan detail + workouts | That plan's writes |
| `tiles/{z}/{x}/{y}.png` | OSM tile images | Upload (pre-fetch for that activity's bbox) |

**Not static:** Map tiles not yet cached fall back to live OSM proxy.

**File volume estimate:** ~8 + 2×N files where N = number of activities. Tile cache grows slowly as new areas are covered; ~100–300 tiles per activity at zoom levels 12–16, ~6MB per activity worst case.

## Rebuild Mechanism

Rebuilds run **asynchronously in the background** — API responses return immediately.

### Trigger Scope

| Write operation | Files rebuilt |
|----------------|---------------|
| Upload `.fit` | `activities.json`, `activity-{id}.json`, `datapoints-{id}.json`, `dashboard.json`, `goals.json`, `shoes.json`, tiles for that activity |
| Delete activity | Same as upload, minus per-activity files (deleted) |
| Coros sync | Full rebuild (all files) |
| Goal create/update/delete | `goals.json`, `dashboard.json` |
| Shoe create/update | `shoes.json` |
| Plan create/delete | `plans.json` |
| Plan workout update | `plan-{id}.json` |

### Implementation: `builder.py`

A new service module with three entry points:

- `rebuild_activity(id)` — generates per-activity files + pre-fetches tiles
- `rebuild_globals()` — generates `activities.json`, `dashboard.json`, `goals.json`, `shoes.json`, `plans.json`
- `rebuild_all()` — calls both for every activity; used after sync or on first startup

All writes are **atomic**: write to `.tmp` file, then `os.replace()` so nginx never serves a partial file.

### Startup Behavior

On backend container start: if `/data/static/activities.json` does not exist, run `rebuild_all()` synchronously before accepting requests. After that, incremental rebuilds only.

## Frontend Changes

Changes are confined to `api/client.ts`. Components and pages are unchanged.

### Read functions → `/static/*.json`

```typescript
export const getActivities   = () => fetch("/static/activities.json").then(r => r.json());
export const getActivityFull = (id) => fetch(`/static/activity-${id}.json`).then(r => r.json());
export const getDataPoints   = (id) => fetch(`/static/datapoints-${id}.json`).then(r => r.json());
export const getDashboard    = () => fetch("/static/dashboard.json").then(r => r.json());
export const getGoals        = () => fetch("/static/goals.json").then(r => r.json());
export const getShoes        = () => fetch("/static/shoes.json").then(r => r.json());
export const getPlans        = () => fetch("/static/plans.json").then(r => r.json());
export const getPlanDetail   = (id) => fetch(`/static/plan-${id}.json`).then(r => r.json());
```

Write functions (`uploadFit`, `createGoal`, `updateGoal`, `deleteGoal`, etc.) are unchanged — still POST/PATCH/DELETE to `/api/`.

### Dashboard consolidation

`getStatsSummary`, `getTrainingLoad`, `getVdot`, `getPersonalBests` collapse into one `getDashboard()` call. Dashboard page goes from 4 API calls to 1 static file fetch.

### Cache invalidation

After mutations, `queryClient.invalidateQueries(...)` triggers a refetch of the relevant static JSON. By the time the user sees the updated UI (~2-3s after mutation), the rebuild has completed.

### staleTime

Static read queries use `staleTime: Infinity` — files only change on explicit writes.

## nginx Configuration

```nginx
# Serve pre-built JSON snapshots
location /static/ {
    alias /data/static/;
    add_header Cache-Control "no-cache";
}

# Serve cached tiles, fall back to FastAPI proxy
location /api/tiles/ {
    try_files /data/static/tiles/$uri @tile_proxy;
}

location @tile_proxy {
    proxy_pass http://backend:8000;
}
```

## docker-compose Changes

Mount the `/data` volume into the frontend container so nginx can serve the static files:

```yaml
frontend:
  volumes:
    - ./data:/data   # add this line
```

## Tradeoffs

| Concern | Impact |
|---------|--------|
| Data freshness | Reads reflect last rebuild (~2-3s after write). Acceptable for a personal log. |
| Disk usage | Small. JSON + tiles grow linearly with activity count. |
| Rebuild time | Full rebuild: a few seconds. Incremental: sub-second for most writes. |
| Complexity | `builder.py` is new code to maintain; tile pre-fetching adds a network call at upload time. |
| Offline maps | Tile cache means maps work without OSM connectivity after first load. |
