import { Paper, Stack, Typography } from "@mui/material";

import { PageHeader } from "@/components/common/page-header";
import { getVentas } from "@/modules/ventas/services/ventas-service";

export default async function VentasPage() {
  const ventas = await getVentas();

  return (
    <>
      <PageHeader title="Ventas" description="Registro de transacciones recientes" />

      <Stack spacing={1.5}>
        {ventas.map((venta) => (
          <Paper key={venta.id} sx={{ p: 2.5 }}>
            <Typography variant="h6">Venta #{venta.id}</Typography>
            <Typography color="text.secondary">
              Fecha: {venta.fecha} | Total: ${venta.total.toFixed(2)} | Estado: {venta.estado}
            </Typography>
          </Paper>
        ))}
      </Stack>
    </>
  );
}
