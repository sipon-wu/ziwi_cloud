export interface User {
  id: string;
  email: string;
  display_name: string;
  tenant_id: string | null;
  products: any[];
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LicenseTicket {
  id: string;
  ticket_no: string;
  tenant_id: string | null;
  tenant_name: string;
  product: string;
  ticket_type: string;
  tier?: string;
  seats?: number;
  deploy_mode?: string;
  status: string;
  requested_expires_at?: string | null;
  license_key?: string | null;
  finance_confirm_by?: string | null;
  approver_id?: string | null;
  assignee_id?: string | null;
  created_at?: string;
  [key: string]: any;
}
