import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getActivities } from "../api/client";
import { useUnits } from "../contexts/UnitsContext";
import type { Activity } from "../types";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const SPORT_COLORS: Record<string, string> = {
  run:          "bg-blue-100 text-blue-800 border-blue-200",
  trail_run:    "bg-green-100 text-green-800 border-green-200",
  cycling:      "bg-yellow-100 text-yellow-800 border-yellow-200",
  swimming:     "bg-cyan-100 text-cyan-800 border-cyan-200",
  walking:      "bg-gray-100 text-gray-700 border-gray-200",
};

function sportColor(sport: string): string {
  return SPORT_COLORS[sport] ?? "bg-purple-100 text-purple-800 border-purple-200";
}

function formatActivityName(act: Activity): string {
  if (act.name) return act.name;
  if (act.planned_workout_type) return act.planned_workout_type;
  return act.sport_type.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

/** Return the Monday of the week containing `d`. */
function weekMonday(d: Date): Date {
  const result = new Date(d);
  const dow = (result.getDay() + 6) % 7; // 0=Mon
  result.setDate(result.getDate() - dow);
  result.setHours(0, 0, 0, 0);
  return result;
}

/** Build a 5-or-6 row calendar grid for the given year/month.
 *  Returns an array of weeks, each week is 7 Date objects. */
function buildCalendarGrid(year: number, month: number): Date[][] {
  const firstDay = new Date(year, month, 1);
  const lastDay  = new Date(year, month + 1, 0);
  const start    = weekMonday(firstDay);
  const weeks: Date[][] = [];
  let current = new Date(start);
  while (current <= lastDay || weeks.length < 4) {
    const week: Date[] = [];
    for (let i = 0; i < 7; i++) {
      week.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    weeks.push(week);
    if (current > lastDay && weeks.length >= 4) break;
  }
  return weeks;
}

export default function CalendarView() {
  const today = new Date();
  const [year, setYear]   = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const { fmtDist } = useUnits();

  const { data: activities = [] } = useQuery<Activity[]>({
    queryKey: ["activities"],
    queryFn: getActivities,
  });

  // Index activities by YYYY-MM-DD
  const byDate: Record<string, Activity[]> = {};
  for (const act of activities) {
    const key = act.started_at.slice(0, 10);
    if (!byDate[key]) byDate[key] = [];
    byDate[key].push(act);
  }

  const weeks = buildCalendarGrid(year, month);
  const monthLabel = new Date(year, month, 1).toLocaleString(undefined, {
    month: "long", year: "numeric",
  });

  function prevMonth() {
    if (month === 0) { setYear(y => y - 1); setMonth(11); }
    else setMonth(m => m - 1);
  }
  function nextMonth() {
    if (month === 11) { setYear(y => y + 1); setMonth(0); }
    else setMonth(m => m + 1);
  }

  return (
    <div className="p-4 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-800">Calendar</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={prevMonth}
            className="px-2 py-1 text-sm text-gray-500 hover:text-gray-800 border border-gray-300 rounded"
          >
            ‹
          </button>
          <span className="text-sm font-semibold text-gray-700 w-36 text-center">{monthLabel}</span>
          <button
            onClick={nextMonth}
            className="px-2 py-1 text-sm text-gray-500 hover:text-gray-800 border border-gray-300 rounded"
          >
            ›
          </button>
          <button
            onClick={() => { setYear(today.getFullYear()); setMonth(today.getMonth()); }}
            className="px-2 py-1 text-xs text-blue-600 border border-blue-300 rounded hover:bg-blue-50"
          >
            Today
          </button>
        </div>
      </div>

      {/* Day header */}
      <div className="grid grid-cols-7 mb-1">
        {DAYS.map((d) => (
          <div key={d} className="text-center text-xs font-semibold text-gray-400 py-1">{d}</div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="border-t border-l border-gray-200 rounded-lg overflow-hidden">
        {weeks.map((week, wi) => (
          <div key={wi} className="grid grid-cols-7 border-b border-gray-200">
            {week.map((day, di) => {
              const key = day.toISOString().slice(0, 10);
              const isCurrentMonth = day.getMonth() === month;
              const isToday = key === today.toISOString().slice(0, 10);
              const acts = byDate[key] ?? [];

              return (
                <div
                  key={di}
                  className={`border-r border-gray-200 min-h-[88px] p-1.5 ${
                    isCurrentMonth ? "bg-white" : "bg-gray-50"
                  }`}
                >
                  <div className={`text-xs font-medium mb-1 w-6 h-6 flex items-center justify-center rounded-full ${
                    isToday
                      ? "bg-blue-600 text-white"
                      : isCurrentMonth ? "text-gray-700" : "text-gray-300"
                  }`}>
                    {day.getDate()}
                  </div>
                  <div className="space-y-0.5">
                    {acts.map((act) => (
                      <Link
                        key={act.id}
                        to={`/activities/${act.id}`}
                        className={`block text-xs px-1.5 py-0.5 rounded border truncate hover:opacity-80 transition-opacity ${sportColor(act.sport_type)}`}
                        title={`${formatActivityName(act)} — ${fmtDist(act.distance_m)}`}
                      >
                        <span className="font-medium">{fmtDist(act.distance_m)}</span>
                        {" "}
                        <span className="opacity-75">{formatActivityName(act)}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
