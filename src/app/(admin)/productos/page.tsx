import { Paper, Stack, Typography } from "@mui/material";

import { PageHeader } from "@/components/common/page-header";
import { getProductos } from "@/modules/productos/services/productos-service";

export default async function ProductosPage() {
  const productos = await getProductos();

  return (
    <>
      <PageHeader title="Productos" description="Catálogo y stock disponible" />

      <Stack spacing={1.5}>
        {productos.map((producto) => (
          <Paper key={producto.id} sx={{ p: 2.5 }}>
            <Typography variant="h6">{producto.nombre}</Typography>
            <Typography color="text.secondary">
              Precio: ${producto.precio.toFixed(2)} | Stock: {producto.stock}
            </Typography>
          </Paper>
        ))}
      </Stack>
    </>
  );
}
