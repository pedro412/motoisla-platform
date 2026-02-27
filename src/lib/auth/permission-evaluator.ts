import type { AuthSession } from "@/types/auth";
import type { AdminModule, AppNavItem } from "@/types/navigation";

export interface PermissionEvaluator {
  canAccessModule(session: AuthSession, module: AdminModule): boolean;
  canViewNavItem(session: AuthSession, navItem: AppNavItem): boolean;
}
