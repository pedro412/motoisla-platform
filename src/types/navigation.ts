import type { ReactNode } from "react";

export type AdminModule = "dashboard" | "productos" | "ventas";

export interface AppNavItem {
  key: string;
  label: string;
  href: string;
  icon: ReactNode;
  module: AdminModule;
  requiredPermissions?: string[];
}
