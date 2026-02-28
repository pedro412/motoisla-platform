"use client";

import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Pagination,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/page-header";
import { MoneyInput } from "@/components/forms/money-input";
import { ApiError } from "@/lib/api/errors";
import { investorsService } from "@/modules/investors/services/investors.service";
import { formatCurrency } from "@/modules/products/utils";

const pageSize = 20;

function useDebouncedValue<T>(value: T, delayMs: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedValue(value);
    }, delayMs);

    return () => window.clearTimeout(timer);
  }, [delayMs, value]);

  return debouncedValue;
}

function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    return error.detail;
  }
  return fallback;
}

export function InvestorsListPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createCapital, setCreateCapital] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const debouncedSearch = useDebouncedValue(search.trim(), 300);

  const investorsQuery = useQuery({
    queryKey: ["investors", debouncedSearch, page],
    queryFn: () =>
      investorsService.listInvestors({
        q: debouncedSearch || undefined,
        page,
      }),
  });

  const createInvestorMutation = useMutation({
    mutationFn: () =>
      investorsService.createInvestor({
        display_name: createName.trim(),
        initial_capital: createCapital.trim() ? createCapital.trim() : undefined,
      }),
    onSuccess: async (createdInvestor) => {
      await queryClient.invalidateQueries({ queryKey: ["investors"] });
      setCreateOpen(false);
      setCreateName("");
      setCreateCapital("");
      setCreateError(null);
      router.push(`/investors/${createdInvestor.id}`);
    },
    onError: (error) => {
      setCreateError(getErrorMessage(error, "No fue posible crear el inversionista."));
    },
  });

  const totalPages = Math.max(1, Math.ceil((investorsQuery.data?.count ?? 0) / pageSize));
  const investors = investorsQuery.data?.results ?? [];
  const listError = investorsQuery.isError ? getErrorMessage(investorsQuery.error, "No fue posible cargar los inversionistas.") : null;

  function closeCreateDialog() {
    if (createInvestorMutation.isPending) {
      return;
    }
    setCreateOpen(false);
    setCreateName("");
    setCreateCapital("");
    setCreateError(null);
  }

  async function submitCreateInvestor() {
    if (!createName.trim()) {
      setCreateError("Debes capturar el nombre del inversionista.");
      return;
    }
    setCreateError(null);
    try {
      await createInvestorMutation.mutateAsync();
    } catch {
      return;
    }
  }

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={2} justifyContent="space-between" alignItems={{ md: "center" }}>
        <PageHeader
          title="Inversionistas"
          description="Administra el capital disponible, las compras de productos asignados y el historial financiero de cada inversionista."
        />
        <Button variant="contained" onClick={() => setCreateOpen(true)}>
          Agregar inversionista
        </Button>
      </Stack>

      {listError ? <Alert severity="error">{listError}</Alert> : null}

      <Paper sx={{ p: 2.5 }}>
        <Stack spacing={2}>
          <TextField
            label="Buscar inversionista"
            placeholder="Nombre"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            fullWidth
          />

          {investorsQuery.isLoading ? (
            <Box sx={{ display: "grid", placeItems: "center", py: 6 }}>
              <CircularProgress />
            </Box>
          ) : null}

          {!investorsQuery.isLoading && investors.length === 0 ? (
            <Alert severity="info">Todavía no hay inversionistas registrados.</Alert>
          ) : null}

          {investors.length > 0 ? (
            <TableContainer>
              <Table sx={{ minWidth: 860 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>Nombre</TableCell>
                    <TableCell align="right">Capital disponible</TableCell>
                    <TableCell align="right">Capital invertido</TableCell>
                    <TableCell align="right">Utilidad disponible</TableCell>
                    <TableCell>Estatus</TableCell>
                    <TableCell align="right">Acción</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {investors.map((investor) => (
                    <TableRow key={investor.id} hover>
                      <TableCell>{investor.display_name}</TableCell>
                      <TableCell align="right">{formatCurrency(investor.balances.capital)}</TableCell>
                      <TableCell align="right">{formatCurrency(investor.balances.inventory)}</TableCell>
                      <TableCell align="right">{formatCurrency(investor.balances.profit)}</TableCell>
                      <TableCell>
                        <Chip
                          label={investor.is_active ? "Activo" : "Inactivo"}
                          size="small"
                          color={investor.is_active ? "success" : "default"}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Button variant="outlined" size="small" onClick={() => router.push(`/investors/${investor.id}`)}>
                          Ver detalle
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : null}

          <Box sx={{ display: "flex", justifyContent: "center", pt: 1 }}>
            <Pagination count={totalPages} page={page} onChange={(_event, nextPage) => setPage(nextPage)} color="primary" />
          </Box>
        </Stack>
      </Paper>

      <Dialog
        open={createOpen}
        onClose={closeCreateDialog}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Agregar inversionista</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {createError ? <Alert severity="error">{createError}</Alert> : null}
            <TextField
              label="Nombre"
              value={createName}
              onChange={(event) => setCreateName(event.target.value)}
              fullWidth
              autoFocus
            />
            <MoneyInput
              label="Capital inicial (opcional)"
              value={createCapital}
              onChange={setCreateCapital}
              placeholder="0.00"
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeCreateDialog}>Cancelar</Button>
          <Button variant="contained" onClick={submitCreateInvestor} disabled={createInvestorMutation.isPending}>
            {createInvestorMutation.isPending ? "Guardando..." : "Guardar"}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
