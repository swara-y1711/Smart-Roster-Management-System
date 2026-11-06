export type Database = {
  public: {
    Tables: {
      manager_profiles: {
        Row: {
          id: string;
          full_name: string;
          work_email: string;
          employee_id: string;
          created_at: string;
        };
        Insert: {
          id: string;
          full_name: string;
          work_email: string;
          employee_id: string;
          created_at?: string;
        };
        Update: {
          id?: string;
          full_name?: string;
          work_email?: string;
          employee_id?: string;
          created_at?: string;
        };
        Relationships: [];
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
};
