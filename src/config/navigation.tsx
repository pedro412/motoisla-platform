import DashboardRoundedIcon from "@mui/icons-material/DashboardRounded";
import Inventory2RoundedIcon from "@mui/icons-material/Inventory2Rounded";
import PointOfSaleRoundedIcon from "@mui/icons-material/PointOfSaleRounded";

import type { AppNavItem } from "@/types/navigation";

export const adminNavItems: AppNavItem[] = [
  {
    key: "dashboard",
    label: "Dashboard",
    href: "/dashboard",
    icon: <DashboardRoundedIcon fontSize="small" />,
    module: "dashboard",
  },
  {
    key: "productos",
    label: "Productos",
    href: "/productos",
    icon: <Inventory2RoundedIcon fontSize="small" />,
    module: "productos",
    requiredPermissions: ["productos:read"],
  },
  {
    key: "ventas",
    label: "Ventas",
    href: "/ventas",
    icon: <PointOfSaleRoundedIcon fontSize="small" />,
    module: "ventas",
    requiredPermissions: ["ventas:read"],
  },
];
