import axios from "axios";

const api = axios.create({ baseURL: "/api" });

// Activities
export const getActivities = () => api.get("/activities").then((r) => r.data);
export const getActivity = (id: number) =>
  api.get(`/activities/${id}`).then((r) => r.data);
export const getDataPoints = (id: number) =>
  api.get(`/activities/${id}/datapoints`).then((r) => r.data);
export const getPhotos = (id: number) =>
  api.get(`/activities/${id}/photos`).then((r) => r.data);
export const uploadFit = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return api.post("/activities/upload", fd).then((r) => r.data);
};
export const updateActivity = (id: number, data: object) =>
  api.patch(`/activities/${id}`, data).then((r) => r.data);

// Stats
export const getStatsSummary = (period = "week") =>
  api.get(`/stats/summary?period=${period}`).then((r) => r.data);
export const getTrainingLoad = (days = 90) =>
  api.get(`/stats/training-load?days=${days}`).then((r) => r.data);
export const getVdot = () => api.get("/stats/vdot").then((r) => r.data);
export const getActivityAnalytics = (id: number) =>
  api.get(`/stats/activities/${id}/analytics`).then((r) => r.data);

// Shoes
export const getShoes = () => api.get("/shoes").then((r) => r.data);
export const createShoe = (data: object) =>
  api.post("/shoes", data).then((r) => r.data);
export const updateShoe = (id: number, data: object) =>
  api.patch(`/shoes/${id}`, data).then((r) => r.data);

// Goals
export const getGoals = () => api.get("/goals").then((r) => r.data);
export const createGoal = (data: object) =>
  api.post("/goals", data).then((r) => r.data);
export const deleteGoal = (id: number) => api.delete(`/goals/${id}`);

// Training Plans
export const getPlans = () => api.get("/plans").then((r) => r.data);
export const createPlan = (data: object) =>
  api.post("/plans", data).then((r) => r.data);
export const getPlan = (id: number) =>
  api.get(`/plans/${id}`).then((r) => r.data);
export const getPlanWorkouts = (id: number) =>
  api.get(`/plans/${id}/workouts`).then((r) => r.data);
export const deletePlan = (id: number) => api.delete(`/plans/${id}`);
export const updatePlanWorkout = (
  planId: number,
  workoutId: number,
  data: object
) =>
  api
    .patch(`/plans/${planId}/workouts/${workoutId}`, data)
    .then((r) => r.data);

// Sync
export const getSyncStatus = () => api.get("/sync/status").then((r) => r.data);
export const triggerSync = () => api.post("/sync/trigger").then((r) => r.data);
