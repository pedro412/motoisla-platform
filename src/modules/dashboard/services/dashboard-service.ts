export interface DashboardSummary {
  totalVentasHoy: number;
  totalProductosActivos: number;
  ticketPromedio: number;
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return {
    totalVentasHoy: 24,
    totalProductosActivos: 118,
    ticketPromedio: 42.35,
  };
}
