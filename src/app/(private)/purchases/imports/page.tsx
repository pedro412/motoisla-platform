"use client";

import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Divider,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { ApiError } from "@/lib/api/errors";
import type { ImportLine } from "@/lib/types/purchases";
import { parseMyesaInvoice } from "@/modules/purchases/parsers/myesa.parser";
import { purchasesService } from "@/modules/purchases/services/purchases.service";

const IVA_RATE = 0.16;
const PUBLIC_PRICE_MARKUP = 1.3;

type EditableImportLine = ImportLine & { publicPriceTouched?: boolean };

function parseAmount(value: string | null | undefined): number {
  if (!value) {
    return 0;
  }
  const normalized = value.replace(/,/g, "").trim();
  const numeric = Number(normalized);
  return Number.isFinite(numeric) ? numeric : 0;
}

function toMoney(value: number): string {
  return value.toFixed(2);
}

function formatMaskedMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatMaskedMoneyString(value: string | null | undefined): string | null {
  if (!value?.trim()) {
    return null;
  }
  return formatMaskedMoney(parseAmount(value));
}

function normalizeDecimalForApi(value: string | null | undefined): string | null {
  if (!value?.trim()) {
    return null;
  }
  return value.replace(/,/g, "").trim();
}

function formatMoney(value: number): string {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(value);
}

function rowCostWithTax(line: EditableImportLine): number {
  return parseAmount(line.unit_cost) * (1 + IVA_RATE);
}

function rowMarkupAmount(line: EditableImportLine): number {
  return parseAmount(line.public_price) - rowCostWithTax(line);
}

function rowMarkupPercent(line: EditableImportLine): number {
  const base = rowCostWithTax(line);
  if (base <= 0) {
    return 0;
  }
  return (rowMarkupAmount(line) / base) * 100;
}

function defaultPublicPrice(unitCost: number): number {
  return unitCost * (1 + IVA_RATE) * PUBLIC_PRICE_MARKUP;
}

function toEditableLine(line: ReturnType<typeof parseMyesaInvoice>[number], index: number): EditableImportLine {
  const localId = `preview-${index + 1}-${line.sku || "no-sku"}`;
  return {
    id: localId,
    line_no: index + 1,
    raw_line: line.raw_line,
    parsed_sku: line.sku,
    parsed_name: line.name,
    parsed_qty: line.qty,
    parsed_unit_cost: line.unit_cost,
    parsed_unit_price: line.unit_price,
    sku: line.sku,
    name: line.name,
    qty: line.qty,
    unit_cost: formatMaskedMoneyString(line.unit_cost),
    unit_price: formatMaskedMoneyString(line.unit_price),
    public_price: formatMaskedMoneyString(line.public_price),
    matched_product: null,
    match_status: line.match_status,
    is_selected: line.is_selected,
    notes: line.notes,
    publicPriceTouched: false,
  };
}

export default function PurchasesImportsPage() {
  const [supplierId, setSupplierId] = useState("");
  const [parserId, setParserId] = useState("");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState("");
  const [subtotal, setSubtotal] = useState("");
  const [tax, setTax] = useState("");
  const [total, setTotal] = useState("");
  const [rawText, setRawText] = useState("");
  const [lines, setLines] = useState<EditableImportLine[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const suppliersQuery = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => purchasesService.getSuppliers(),
  });

  const parsersQuery = useQuery({
    queryKey: ["supplier-parsers", supplierId],
    queryFn: () => purchasesService.getParsersBySupplier(supplierId),
    enabled: Boolean(supplierId),
  });

  const computedSubtotal = useMemo(() => {
    return lines
      .filter((line) => line.is_selected)
      .reduce((acc, line) => acc + parseAmount(line.qty) * parseAmount(line.unit_cost), 0);
  }, [lines]);

  const computedTax = useMemo(() => computedSubtotal * IVA_RATE, [computedSubtotal]);
  const computedTotal = useMemo(() => computedSubtotal + parseAmount(tax || toMoney(computedTax)), [computedSubtotal, computedTax, tax]);
  const selectedItemsCount = useMemo(() => lines.filter((line) => line.is_selected).length, [lines]);
  const selectedPiecesCount = useMemo(
    () => lines.filter((line) => line.is_selected).reduce((acc, line) => acc + parseAmount(line.qty), 0),
    [lines],
  );

  function handleParse() {
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!supplierId || !parserId) {
      setErrorMessage("Selecciona proveedor y tipo de factura antes de parsear.");
      return;
    }

    if (!rawText.trim()) {
      setErrorMessage("Pega el texto de la factura antes de parsear.");
      return;
    }

    const selectedParser = parsersQuery.data?.results.find((parser) => parser.id === parserId);
    if (!selectedParser) {
      setErrorMessage("No fue posible resolver el parser seleccionado.");
      return;
    }

    if (selectedParser.parser_key !== "myesa") {
      setErrorMessage(`Parser ${selectedParser.parser_key} no soportado en cliente por ahora.`);
      return;
    }

    const parsedLines = parseMyesaInvoice(rawText).map(toEditableLine);
    setLines(parsedLines);

    const parsedSubtotal = parsedLines
      .filter((line) => line.is_selected)
      .reduce((acc, line) => acc + parseAmount(line.qty) * parseAmount(line.unit_cost), 0);
    const parsedTax = parsedSubtotal * IVA_RATE;

    if (!subtotal) {
      setSubtotal(toMoney(parsedSubtotal));
    }
    if (!tax) {
      setTax(toMoney(parsedTax));
    }
    if (!total) {
      setTotal(toMoney(parsedSubtotal + parsedTax));
    }

    setSuccessMessage(`Preview generado en cliente con ${parsedLines.length} líneas.`);
  }

  function handleLineUpdate(line: EditableImportLine, patch: Partial<EditableImportLine>) {
    setErrorMessage(null);

    const nextLine: EditableImportLine = { ...line, ...patch };
    if (patch.unit_cost !== undefined && !line.publicPriceTouched) {
      const unitCost = parseAmount(String(patch.unit_cost));
      nextLine.public_price = formatMaskedMoney(defaultPublicPrice(unitCost));
    }
    if (patch.public_price !== undefined) {
      nextLine.publicPriceTouched = true;
    }

    setLines((prev) => prev.map((item) => (item.id === line.id ? nextLine : item)));
  }

  async function confirmBatch() {
    if (!supplierId || !parserId) {
      setErrorMessage("Selecciona proveedor y tipo de factura antes de confirmar.");
      return;
    }

    if (!lines.length) {
      setErrorMessage("No hay líneas en preview para confirmar.");
      return;
    }

    setErrorMessage(null);
    setSuccessMessage(null);
    setWorking(true);
    try {
      const confirmed = await purchasesService.previewConfirm({
        supplier: supplierId,
        parser: parserId,
        invoice_number: invoiceNumber || undefined,
        invoice_date: invoiceDate || undefined,
        subtotal: subtotal || undefined,
        tax: tax || undefined,
        total: total || undefined,
        raw_text: rawText,
        lines: lines.map((line) => ({
          sku: line.sku,
          name: line.name,
          qty: line.qty,
          unit_cost: normalizeDecimalForApi(line.unit_cost),
          unit_price: normalizeDecimalForApi(line.unit_price),
          public_price: normalizeDecimalForApi(line.public_price),
          is_selected: line.is_selected,
          notes: line.notes,
        })),
      });

      setSuccessMessage(`Compra confirmada. Batch: ${confirmed.batch_id} / Receipt: ${confirmed.purchase_receipt_id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === "subtotal_mismatch") {
          const batchSubtotal = String(error.fields.batch_subtotal ?? "?");
          const computed = String(error.fields.computed_subtotal ?? "?");
          setErrorMessage(`Subtotal no coincide. Factura: ${batchSubtotal} / Líneas: ${computed}`);
        } else {
          setErrorMessage(error.detail);
        }
      } else {
        setErrorMessage("No fue posible confirmar la compra.");
      }
    } finally {
      setWorking(false);
    }
  }

  return (
    <Stack spacing={3}>
      <Typography variant="h4">Compras (Importación factura)</Typography>
      <Typography color="text.secondary">
        Flujo: parse local inmediato - preview editable - confirmación segura en backend.
      </Typography>

      {errorMessage ? <Alert severity="error">{errorMessage}</Alert> : null}
      {successMessage ? <Alert severity="success">{successMessage}</Alert> : null}

      <Paper sx={{ p: 2.5 }}>
        <Stack spacing={2}>
          <Typography variant="h6">Encabezado</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <TextField
              select
              label="Proveedor"
              value={supplierId}
              onChange={(event) => {
                setSupplierId(event.target.value);
                setParserId("");
              }}
              fullWidth
            >
              {(suppliersQuery.data?.results ?? []).map((supplier) => (
                <MenuItem key={supplier.id} value={supplier.id}>
                  {supplier.code} - {supplier.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField select label="Tipo factura" value={parserId} onChange={(event) => setParserId(event.target.value)} fullWidth>
              {(parsersQuery.data?.results ?? []).map((parser) => (
                <MenuItem key={parser.id} value={parser.id}>
                  {parser.parser_key.toUpperCase()} v{parser.version}
                </MenuItem>
              ))}
            </TextField>
          </Stack>

          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <TextField label="No. Factura" value={invoiceNumber} onChange={(event) => setInvoiceNumber(event.target.value)} fullWidth />
            <TextField
              label="Fecha"
              type="date"
              value={invoiceDate}
              onChange={(event) => setInvoiceDate(event.target.value)}
              InputLabelProps={{ shrink: true }}
              fullWidth
            />
          </Stack>

          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <TextField
              label="Subtotal"
              value={subtotal}
              onChange={(event) => setSubtotal(event.target.value)}
              helperText={`Calculado: ${toMoney(computedSubtotal)}`}
              fullWidth
            />
            <TextField
              label="IVA"
              value={tax}
              onChange={(event) => setTax(event.target.value)}
              helperText={`Calculado 16%: ${toMoney(computedTax)}`}
              fullWidth
            />
            <TextField
              label="Total"
              value={total}
              onChange={(event) => setTotal(event.target.value)}
              helperText={`Calculado: ${toMoney(computedTotal)}`}
              fullWidth
            />
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2.5 }}>
        <Stack spacing={1.5}>
          <Typography variant="h6">Texto factura</Typography>
          <TextField
            multiline
            minRows={8}
            placeholder="Pega aquí la factura MYESA"
            value={rawText}
            onChange={(event) => setRawText(event.target.value)}
            fullWidth
          />
          <Button variant="contained" onClick={handleParse} disabled={working}>
            {working ? <CircularProgress color="inherit" size={20} /> : "Parsear factura"}
          </Button>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2.5 }}>
        <Stack spacing={2}>
          <Typography variant="h6">Preview editable</Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Sel</TableCell>
                  <TableCell>SKU</TableCell>
                  <TableCell>Descripción</TableCell>
                  <TableCell>Qty</TableCell>
                  <TableCell>Costo</TableCell>
                  <TableCell>Venta</TableCell>
                  <TableCell>Precio público</TableCell>
                  <TableCell>Margen</TableCell>
                  <TableCell>Imagen</TableCell>
                  <TableCell>Match</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {lines.map((line) => (
                  <TableRow key={line.id}>
                    <TableCell>
                      <Checkbox
                        checked={line.is_selected}
                        onChange={(event) => handleLineUpdate(line, { is_selected: event.target.checked })}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={line.sku}
                        onChange={(event) => handleLineUpdate(line, { sku: event.target.value })}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        multiline
                        minRows={2}
                        value={line.name}
                        onChange={(event) => handleLineUpdate(line, { name: event.target.value })}
                        sx={{ minWidth: 380 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={line.qty ?? ""}
                        onChange={(event) => handleLineUpdate(line, { qty: event.target.value })}
                        sx={{ width: 90 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={line.unit_cost ?? ""}
                        onChange={(event) => handleLineUpdate(line, { unit_cost: event.target.value })}
                        onBlur={() =>
                          handleLineUpdate(line, {
                            unit_cost: formatMaskedMoneyString(line.unit_cost),
                          })
                        }
                        sx={{ width: 110 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={line.unit_price ?? ""}
                        onChange={(event) => handleLineUpdate(line, { unit_price: event.target.value })}
                        onBlur={() =>
                          handleLineUpdate(line, {
                            unit_price: formatMaskedMoneyString(line.unit_price),
                          })
                        }
                        sx={{ width: 110 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={line.public_price ?? ""}
                        onChange={(event) => handleLineUpdate(line, { public_price: event.target.value })}
                        onBlur={() =>
                          handleLineUpdate(line, {
                            public_price: formatMaskedMoneyString(line.public_price),
                          })
                        }
                        sx={{ width: 120 }}
                      />
                    </TableCell>
                    <TableCell>
                      <Stack>
                        <Typography variant="caption">{formatMoney(rowMarkupAmount(line))}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {rowMarkupPercent(line).toFixed(2)}%
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        Próximamente
                      </Typography>
                    </TableCell>
                    <TableCell>{line.match_status}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <Divider />
          <Box>
            <Typography>Total artículos seleccionados: {selectedItemsCount}</Typography>
            <Typography>Total piezas seleccionadas: {selectedPiecesCount.toFixed(2)}</Typography>
            <Typography>Subtotal líneas seleccionadas: {formatMoney(computedSubtotal)}</Typography>
            <Typography>IVA (16%): {formatMoney(parseAmount(tax || toMoney(computedTax)))}</Typography>
            <Typography variant="h6">Total: {formatMoney(parseAmount(total || toMoney(computedTotal)))}</Typography>
          </Box>

          <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
            <Button variant="contained" onClick={confirmBatch} disabled={!lines.length || working}>
              {working ? <CircularProgress color="inherit" size={20} /> : "Confirmar compra"}
            </Button>
          </Stack>
        </Stack>
      </Paper>
    </Stack>
  );
}
