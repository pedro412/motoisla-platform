"use client";

import { Alert, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { purchasesService } from "@/modules/purchases/services/purchases.service";

function formatMoney(value: string | null) {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(amount);
}

export default function PurchaseReceiptDetailPage() {
  const params = useParams<{ id: string }>();
  const receiptId = params.id ?? "";

  const receiptQuery = useQuery({
    queryKey: ["purchase-receipt", receiptId],
    queryFn: () => purchasesService.getPurchaseReceipt(receiptId),
    enabled: Boolean(receiptId),
  });

  if (receiptQuery.isLoading) {
    return <Typography>Cargando factura...</Typography>;
  }

  if (receiptQuery.isError || !receiptQuery.data) {
    return <Alert severity="error">No fue posible cargar la factura.</Alert>;
  }

  const receipt = receiptQuery.data;

  return (
    <Stack spacing={3}>
      <Typography variant="h4">Factura {receipt.invoice_number || receipt.id.slice(0, 8)}</Typography>
      <Paper sx={{ p: 2.5 }}>
        <Stack spacing={0.75}>
          <Typography>Proveedor: {receipt.supplier_code} - {receipt.supplier_name}</Typography>
          <Typography>Fecha: {receipt.invoice_date || "-"}</Typography>
          <Typography>Estatus: {receipt.status}</Typography>
          <Typography>Total: {formatMoney(receipt.total)}</Typography>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2.5 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>SKU</TableCell>
                <TableCell>Producto</TableCell>
                <TableCell>Cantidad</TableCell>
                <TableCell>Costo</TableCell>
                <TableCell>Venta</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {receipt.lines.map((line) => (
                <TableRow key={line.id}>
                  <TableCell>{line.product_sku}</TableCell>
                  <TableCell>{line.product_name}</TableCell>
                  <TableCell>{line.qty}</TableCell>
                  <TableCell>{formatMoney(line.unit_cost)}</TableCell>
                  <TableCell>{formatMoney(line.unit_price)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Stack>
  );
}
