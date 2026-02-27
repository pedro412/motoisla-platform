"use client";

import { Box, Toolbar } from "@mui/material";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { usePathname } from "next/navigation";

import { AppSidebar, DRAWER_WIDTH } from "@/components/layout/app-sidebar";
import { AppTopbar } from "@/components/layout/app-topbar";
import { adminNavItems } from "@/config/navigation";

interface AppShellProps {
  children: ReactNode;
}

function getTitleFromPath(pathname: string): string {
  if (pathname.startsWith("/productos")) {
    return "Productos";
  }

  if (pathname.startsWith("/ventas")) {
    return "Ventas";
  }

  return "Dashboard";
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const title = useMemo(() => getTitleFromPath(pathname), [pathname]);

  return (
    <Box sx={{ display: "flex", minHeight: "100dvh" }}>
      <AppTopbar title={title} onOpenMobileMenu={() => setMobileOpen(true)} />
      <AppSidebar navItems={adminNavItems} mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2, md: 3 },
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: { md: `${DRAWER_WIDTH}px` },
        }}
      >
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}
