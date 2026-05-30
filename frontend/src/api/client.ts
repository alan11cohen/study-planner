const BASE = "/api";

export type TokenPayload = { sub: string; name: string; exp: number };

export function getToken(): string | null {
  return localStorage.getItem("token");
}

export function setToken(token: string): void {
  localStorage.setItem("token", token);
}

export function clearToken(): void {
  localStorage.removeItem("token");
}

export function getTokenPayload(): TokenPayload | null {
  const token = getToken();
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1])) as TokenPayload;
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      clearToken();
      return null;
    }
    return payload;
  } catch {
    return null;
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...init,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

export type User = { id: number; name: string };
export type StudyPlan = {
  id: number;
  user_id: number;
  goal: string;
  hours_per_week: number;
  description: string | null;
  target_date: string | null;
};
export type StudyTask = {
  id: number;
  plan_id: number;
  title: string;
  estimated_hours: number;
  completed: boolean;
};
export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export const api = {
  register: (name: string, password: string) =>
    req<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, password }),
    }),

  login: (name: string, password: string) =>
    req<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ name, password }),
    }),

  getUsers: () => req<User[]>("/users"),

  getUser: (id: number) => req<User>(`/users/${id}`),

  getUserPlans: (userId: number) => req<StudyPlan[]>(`/users/${userId}/plans`),

  createPlan: (data: {
    user_id: number;
    goal: string;
    hours_per_week: number;
    description?: string | null;
    target_date?: string | null;
  }) =>
    req<StudyPlan>("/plans", { method: "POST", body: JSON.stringify(data) }),

  getPlan: (id: number) => req<StudyPlan>(`/plans/${id}`),

  updatePlan: (
    planId: number,
    data: Partial<Pick<StudyPlan, "description" | "target_date">>,
  ) =>
    req<StudyPlan>(`/plans/${planId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  createTask: (
    planId: number,
    data: { title: string; estimated_hours: number },
  ) =>
    req<StudyTask>(`/plans/${planId}/tasks`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getTasks: (planId: number) => req<StudyTask[]>(`/plans/${planId}/tasks`),

  toggleTask: (planId: number, taskId: number, completed: boolean) =>
    req<StudyTask>(`/plans/${planId}/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify({ completed }),
    }),
};
