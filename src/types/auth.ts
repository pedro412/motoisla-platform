export interface AuthSession {
  userId?: string;
  role?: string;
  permissions?: string[];
  isAuthenticated: boolean;
}
