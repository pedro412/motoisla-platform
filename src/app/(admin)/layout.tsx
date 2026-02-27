import type { ReactNode } from "react";

import { AppShell } from "@/components/layout/app-shell";

interface AdminLayoutProps {
  children: ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  return <AppShell>{children}</AppShell>;
}
