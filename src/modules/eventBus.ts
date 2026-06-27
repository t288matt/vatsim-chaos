interface EventMap {
  [key: string]: any
}

class EventBus<Events extends EventMap = EventMap> {
  private listeners = new Map<keyof Events, Set<(payload: any) => void>>()

  on<K extends keyof Events>(
    event: K,
    listener: (payload: Events[K]) => void
  ): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(listener)

    return () => this.off(event, listener)
  }

  emit<K extends keyof Events>(event: K, payload: Events[K]): void {
    const eventListeners = this.listeners.get(event)
    if (eventListeners) {
      eventListeners.forEach(listener => listener(payload))
    }
  }

  off<K extends keyof Events>(event: K, listener: (payload: Events[K]) => void): void {
    const eventListeners = this.listeners.get(event)
    if (eventListeners) {
      eventListeners.delete(listener)
    }
  }
}

export interface AppEvents {
  'files:uploaded':        { count: number };
  'files:loaded':          { files: Array<{ id: string; name: string; size: number; upload_date: number }> };
  'validation:changed':    { filename: string; result: { valid: boolean; error?: string; flight_count?: number; flights?: Array<{ origin: string; destination: string; aircraft_type: string; waypoint_count: number }> } };
  'files:selected':        { files: Array<{ filename: string; valid: boolean; flight_count: number; error?: string }> };
  'processing:completed':  { processingTime: number };
  'duplicates:detected':   { hasDuplicates: boolean; routes: Array<{ origin: string; destination: string; count: number; files: string[] }> };
}

export const bus = new EventBus<AppEvents>()
export { EventBus }
