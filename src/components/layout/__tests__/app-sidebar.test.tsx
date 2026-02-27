import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { adminNavItems } from "@/config/navigation";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

describe("AppSidebar", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders all configured navigation items", () => {
    render(<AppSidebar navItems={adminNavItems} mobileOpen={false} onMobileClose={vi.fn()} />);

    expect(screen.getAllByText("Dashboard").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Productos").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ventas").length).toBeGreaterThan(0);
  });
});
