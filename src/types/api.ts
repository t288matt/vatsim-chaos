export interface ApiOk<T> { ok: true; data: T }
export interface ApiError { ok: false; error: string }
export type ApiResponse<T> = ApiOk<T> | ApiError;

export interface FileInfo {
    id: string;
    name: string;
    size: number;
    upload_date: number;
}

export interface ValidationResult {
    valid: boolean;
    flight_count: number;
    error?: string;
    flights: Array<{
        origin: string;
        destination: string;
        aircraft_type: string;
        waypoint_count: number;
    }>;
}

export interface ProcessingStatus {
    is_processing: boolean;
    current_step: number;
    total_steps: number;
    completed: boolean;
    failed: boolean;
    error: string | null;
    start_time: string | null;
    end_time: string | null;
}
