export type Database = {
  public: {
    Tables: {
      organizations: {
        Row: {
          id: string;
          name: string;
          created_at: string;
        };
        Insert: {
          id?: string;
          name: string;
          created_at?: string;
        };
        Update: {
          id?: string;
          name?: string;
          created_at?: string;
        };
        Relationships: [];
      };
      organization_members: {
        Row: {
          id: string;
          organization_id: string;
          manager_id: string;
          created_at: string;
        };
        Insert: {
          id?: string;
          organization_id: string;
          manager_id: string;
          created_at?: string;
        };
        Update: {
          id?: string;
          organization_id?: string;
          manager_id?: string;
          created_at?: string;
        };
        Relationships: [
          {
            foreignKeyName: "organization_members_manager_id_fkey";
            columns: ["manager_id"];
            isOneToOne: false;
            referencedRelation: "manager_profiles";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "organization_members_organization_id_fkey";
            columns: ["organization_id"];
            isOneToOne: false;
            referencedRelation: "organizations";
            referencedColumns: ["id"];
          },
        ];
      };
      brands: {
        Row: {
          id: string;
          organization_id: string;
          name: string;
          industry: string | null;
          description: string | null;
          created_at: string | null;
        };
        Insert: {
          id?: string;
          organization_id: string;
          name: string;
          industry?: string | null;
          description?: string | null;
          created_at?: string | null;
        };
        Update: {
          id?: string;
          organization_id?: string;
          name?: string;
          industry?: string | null;
          description?: string | null;
          created_at?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "brands_organization_id_fkey";
            columns: ["organization_id"];
            isOneToOne: false;
            referencedRelation: "organizations";
            referencedColumns: ["id"];
          },
        ];
      };
      processes: {
        Row: {
          id: string;
          brand_id: string;
          name: string;
          description: string | null;
          created_at: string | null;
        };
        Insert: {
          id?: string;
          brand_id: string;
          name: string;
          description?: string | null;
          created_at?: string | null;
        };
        Update: {
          id?: string;
          brand_id?: string;
          name?: string;
          description?: string | null;
          created_at?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "processes_brand_id_fkey";
            columns: ["brand_id"];
            isOneToOne: false;
            referencedRelation: "brands";
            referencedColumns: ["id"];
          },
        ];
      };
      pods: {
        Row: {
          id: string;
          process_id: string;
          name: string;
          description: string | null;
          created_at: string | null;
        };
        Insert: {
          id?: string;
          process_id: string;
          name: string;
          description?: string | null;
          created_at?: string | null;
        };
        Update: {
          id?: string;
          process_id?: string;
          name?: string;
          description?: string | null;
          created_at?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "pods_process_id_fkey";
            columns: ["process_id"];
            isOneToOne: false;
            referencedRelation: "processes";
            referencedColumns: ["id"];
          },
        ];
      };
      employees: {
        Row: {
          id: string;
          organization_id: string;
          employee_code: string;
          first_name: string;
          last_name: string | null;
          email: string;
          phone: string | null;
          employment_type: string | null;
          status: string;
          max_hours_per_week: number | null;
          designation: string;
          created_at: string | null;
        };
        Insert: {
          id?: string;
          organization_id: string;
          employee_code: string;
          first_name: string;
          last_name?: string | null;
          email: string;
          phone?: string | null;
          employment_type?: string | null;
          status?: string;
          max_hours_per_week?: number | null;
          designation: string;
          created_at?: string | null;
        };
        Update: {
          id?: string;
          organization_id?: string;
          employee_code?: string;
          first_name?: string;
          last_name?: string | null;
          email?: string;
          phone?: string | null;
          employment_type?: string | null;
          status?: string;
          max_hours_per_week?: number | null;
          designation?: string;
          created_at?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "employees_organization_id_fkey";
            columns: ["organization_id"];
            isOneToOne: false;
            referencedRelation: "organizations";
            referencedColumns: ["id"];
          },
        ];
      };
      employee_pods: {
        Row: {
          employee_id: string;
          pod_id: string;
          is_primary: boolean | null;
        };
        Insert: {
          employee_id: string;
          pod_id: string;
          is_primary?: boolean | null;
        };
        Update: {
          employee_id?: string;
          pod_id?: string;
          is_primary?: boolean | null;
        };
        Relationships: [
          {
            foreignKeyName: "employee_pods_employee_id_fkey";
            columns: ["employee_id"];
            isOneToOne: false;
            referencedRelation: "employees";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "employee_pods_pod_id_fkey";
            columns: ["pod_id"];
            isOneToOne: false;
            referencedRelation: "pods";
            referencedColumns: ["id"];
          },
        ];
      };
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
    Functions: {
      create_organization: {
        Args: {
          organization_name: string;
        };
        Returns: {
          id: string;
          name: string;
          created_at: string;
        }[];
      };
    };
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
};
