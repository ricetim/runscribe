import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getGoals, createGoal, deleteGoal } from "../api/client";
import { useUnits } from "../contexts/UnitsContext";

const KM_PER_MI = 1.60934;

interface Goal {
  id: number;
  type: string;
  target_value: number;
  period_start: string;
  period_end: string;
  notes: string | null;
}

interface GoalWithProgress {
  goal: Goal;
  progress_km: number;
}

const GOAL_TYPES = [
  { value: "weekly_distance", label: "Weekly Distance" },
  { value: "monthly_distance", label: "Monthly Distance" },
  { value: "annual_distance", label: "Annual Distance" },
];

function ProgressBar({ pct }: { pct: number }) {
  const clamped = Math.min(pct, 100);
  const color = pct >= 100 ? "bg-green-500" : pct >= 70 ? "bg-blue-500" : "bg-blue-400";
  return (
    <div className="w-full bg-gray-100 rounded-full h-2.5 mt-2">
      <div
        className={`${color} h-2.5 rounded-full transition-all`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

function GoalCard({ item, onDelete }: { item: GoalWithProgress; onDelete: () => void }) {
  const { system } = useUnits();
  const { goal, progress_km } = item;
  const pct = (progress_km / goal.target_value) * 100;
  const typeLabel = GOAL_TYPES.find((t) => t.value === goal.type)?.label ?? goal.type;
  const start = new Date(goal.period_start).toLocaleDateString("en-GB", { month: "short", day: "numeric" });
  const end = new Date(goal.period_end).toLocaleDateString("en-GB", { month: "short", day: "numeric", year: "numeric" });

  const fmtGoalDist = (km: number) =>
    system === "imperial"
      ? (km / KM_PER_MI).toFixed(1) + " mi"
      : km.toFixed(1) + " km";

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-medium text-gray-800">{typeLabel}</div>
          <div className="text-xs text-gray-400 mt-0.5">{start} – {end}</div>
          {goal.notes && <div className="text-xs text-gray-500 mt-1">{goal.notes}</div>}
        </div>
        <div className="text-right">
          <div className={`text-lg font-bold ${pct >= 100 ? "text-green-600" : "text-blue-600"}`}>
            {fmtGoalDist(progress_km)}
          </div>
          <div className="text-xs text-gray-400">of {fmtGoalDist(goal.target_value)}</div>
        </div>
      </div>
      <ProgressBar pct={pct} />
      <div className="flex items-center justify-between mt-2">
        <div className="text-xs text-gray-400">{pct.toFixed(0)}% complete</div>
        <button
          onClick={onDelete}
          className="text-xs text-gray-400 hover:text-red-500"
        >
          Delete
        </button>
      </div>
    </div>
  );
}

export default function Goals() {
  const qc = useQueryClient();
  const { system } = useUnits();
  const [showForm, setShowForm] = useState(false);
  const today = new Date().toISOString().slice(0, 10);
  const yearEnd = `${new Date().getFullYear()}-12-31`;

  const defaultTarget = system === "imperial" ? "62" : "100"; // ~100 km in miles
  const [form, setForm] = useState({
    type: "monthly_distance",
    target_value: defaultTarget,
    period_start: today,
    period_end: yearEnd,
    notes: "",
  });

  const { data: goals = [] } = useQuery<GoalWithProgress[]>({
    queryKey: ["goals"],
    queryFn: getGoals,
  });

  const createMutation = useMutation({
    mutationFn: () => {
      const targetKm = system === "imperial"
        ? parseFloat(form.target_value) * KM_PER_MI
        : parseFloat(form.target_value);
      return createGoal({
        type: form.type,
        target_value: targetKm,
        period_start: form.period_start,
        period_end: form.period_end,
        notes: form.notes || null,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["goals"] });
      setShowForm(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteGoal,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["goals"] }),
  });

  return (
    <div className="p-4 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Goals</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + New Goal
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">New Goal</h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Type</label>
              <select
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                value={form.type}
                onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
              >
                {GOAL_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Target ({system === "imperial" ? "mi" : "km"})
              </label>
              <input
                type="number"
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                value={form.target_value}
                onChange={(e) => setForm((f) => ({ ...f, target_value: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Notes</label>
              <input
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                placeholder="Optional"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Start date</label>
              <input
                type="date"
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                value={form.period_start}
                onChange={(e) => setForm((f) => ({ ...f, period_start: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">End date</label>
              <input
                type="date"
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                value={form.period_end}
                onChange={(e) => setForm((f) => ({ ...f, period_end: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded"
            >
              Cancel
            </button>
            <button
              onClick={() => createMutation.mutate()}
              disabled={!form.target_value || createMutation.isPending}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50"
            >
              Save
            </button>
          </div>
        </div>
      )}

      {goals.length === 0 && !showForm ? (
        <div className="text-center text-gray-400 text-sm py-12">
          No goals yet. Set your first distance goal!
        </div>
      ) : (
        <div className="space-y-3">
          {goals.map((item) => (
            <GoalCard
              key={item.goal.id}
              item={item}
              onDelete={() => deleteMutation.mutate(item.goal.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
