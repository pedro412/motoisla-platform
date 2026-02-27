import { Card, CardContent, Grid, Typography } from "@mui/material";

import { PageHeader } from "@/components/common/page-header";
import { getDashboardSummary } from "@/modules/dashboard/services/dashboard-service";

export default async function DashboardPage() {
  const summary = await getDashboardSummary();

  return (
    <>
      <PageHeader title="Dashboard" description="Resumen general del negocio" />

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Ventas de hoy
              </Typography>
              <Typography variant="h4">{summary.totalVentasHoy}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Productos activos
              </Typography>
              <Typography variant="h4">{summary.totalProductosActivos}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Ticket promedio
              </Typography>
              <Typography variant="h4">${summary.ticketPromedio.toFixed(2)}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </>
  );
}
