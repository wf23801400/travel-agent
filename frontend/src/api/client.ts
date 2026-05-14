const API_BASE = 'http://localhost:8000';

export interface Location {
  name: string;
  address: string;
  lat: number;
  lng: number;
  rating?: number;
}

export interface TimeSlot {
  start_time: string;
  end_time: string;
  activity_name: string;
  activity_type: string;
  location?: Location;
  cost: number;
  notes?: string;
}

export interface DayPlan {
  date: string;
  time_slots: TimeSlot[];
}

export interface Itinerary {
  days: DayPlan[];
  total_budget_estimate: number;
  tips: string[];
}

export interface TravelRequest {
  origin?: string;
  destination: string;
  start_date: string;
  end_date: string;
  travelers: number;
  budget_amount?: number;
  pace: 'relaxed' | 'moderate' | 'intensive';
  interests: string[];
  dietary_restrictions?: string[];
}

export async function planTrip(request: TravelRequest): Promise<Itinerary> {
  const res = await fetch(`${API_BASE}/api/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error(`Plan failed: ${res.status}`);
  return res.json();
}

export async function refinePlan(
  request: TravelRequest,
  feedback: string
): Promise<Itinerary> {
  const res = await fetch(`${API_BASE}/api/plan/refine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request, feedback }),
  });
  if (!res.ok) throw new Error(`Refine failed: ${res.status}`);
  return res.json();
}
