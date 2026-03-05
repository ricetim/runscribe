import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { UnitsProvider, useUnits } from "./contexts/UnitsContext";
import ActivityList from "./pages/ActivityList";
import Dashboard from "./pages/Dashboard";
import Gear from "./pages/Gear";
import Goals from "./pages/Goals";
import Plans from "./pages/Plans";
import PlanDetail from "./pages/PlanDetail";
import CalendarView from "./pages/CalendarView";

// Lazy-load ActivityDetail so Leaflet only initialises when the map is needed
const ActivityDetail = lazy(() => import("./pages/ActivityDetail"));

const queryClient = new QueryClient();

function Nav() {
  const { system, toggle } = useUnits();
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded text-sm font-medium ${
      isActive
        ? "bg-blue-700 text-white"
        : "text-blue-100 hover:bg-blue-700 hover:text-white"
    }`;
  return (
    <nav className="bg-blue-800 text-white px-4 py-2 flex gap-2 items-center">
      <span className="font-bold text-lg mr-4">RunScribe</span>
      <NavLink to="/" end className={linkClass}>Dashboard</NavLink>
      <NavLink to="/activities" className={linkClass}>Activities</NavLink>
      <NavLink to="/calendar" className={linkClass}>Calendar</NavLink>
      <NavLink to="/gear" className={linkClass}>Gear</NavLink>
      <NavLink to="/goals" className={linkClass}>Goals</NavLink>
      <NavLink to="/plans" className={linkClass}>Plans</NavLink>
      <button
        onClick={toggle}
        className="ml-auto px-2.5 py-1 rounded text-xs font-semibold bg-blue-700 hover:bg-blue-600 text-blue-100 border border-blue-600 transition-colors"
        title="Toggle units"
      >
        {system === "imperial" ? "mi" : "km"}
      </button>
    </nav>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <UnitsProvider>
      <BrowserRouter>
        <div className="min-h-screen">
          <Nav />
          <main>
            <Suspense fallback={<div className="p-8 text-center text-gray-400">Loading…</div>}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/activities" element={<ActivityList />} />
                <Route path="/activities/:id" element={<ActivityDetail />} />
                <Route path="/gear" element={<Gear />} />
                <Route path="/goals" element={<Goals />} />
                <Route path="/plans" element={<Plans />} />
                <Route path="/plans/:id" element={<PlanDetail />} />
                <Route path="/calendar" element={<CalendarView />} />
              </Routes>
            </Suspense>
          </main>
        </div>
      </BrowserRouter>
      </UnitsProvider>
    </QueryClientProvider>
  );
}
