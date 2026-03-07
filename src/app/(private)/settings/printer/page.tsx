"use client";

import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import UsbRoundedIcon from "@mui/icons-material/UsbRounded";
import PrintRoundedIcon from "@mui/icons-material/PrintRounded";
import { useEffect, useState } from "react";

import { usePrinterStore } from "@/store/printer-store";
import { buildTestTicketBytes } from "@/lib/print/escpos";
import { getAuthorizedDevices, isWebUsbSupported, printViaUSB, requestDevice } from "@/lib/print/usb-printer";

const PAPER_WIDTHS: { label: string; value: 32 | 42 | 48; mm: string }[] = [
  { label: "58 mm", value: 32, mm: "32 chars" },
  { label: "80 mm", value: 42, mm: "42 chars" },
  { label: "110 mm", value: 48, mm: "48 chars" },
];

export default function PrinterSettingsPage() {
  const { charWidth, storeAddress, storePhone, status, errorMessage, setCharWidth, setStoreAddress, setStorePhone, setStatus } =
    usePrinterStore();

  // Lazy initializers avoid setState calls inside the effect body
  const [supported] = useState(() => isWebUsbSupported());
  const [device, setDevice] = useState<USBDevice | null>(null);
  const [detecting, setDetecting] = useState(supported);

  useEffect(() => {
    if (!supported) return;

    let cancelled = false;
    getAuthorizedDevices().then((devices) => {
      if (!cancelled) {
        setDevice(devices[0] ?? null);
        setDetecting(false);
      }
    });

    function onConnect(event: USBConnectionEvent) {
      setDevice(event.device);
    }
    function onDisconnect(event: USBConnectionEvent) {
      setDevice((prev) => (prev?.serialNumber === event.device.serialNumber ? null : prev));
    }
    navigator.usb.addEventListener("connect", onConnect);
    navigator.usb.addEventListener("disconnect", onDisconnect);

    return () => {
      cancelled = true;
      navigator.usb.removeEventListener("connect", onConnect);
      navigator.usb.removeEventListener("disconnect", onDisconnect);
    };
  }, [supported]);

  async function handleConnect() {
    setStatus("idle");
    try {
      const selected = await requestDevice();
      setDevice(selected);
    } catch {
      // User cancelled the picker — not an error
    }
  }

  async function handleTestPrint() {
    setStatus("printing");
    try {
      const bytes = buildTestTicketBytes({ charWidth, storeAddress, storePhone });
      await printViaUSB(bytes);
      setStatus("idle");
    } catch (err) {
      setStatus("error", err instanceof Error ? err.message : "Error al imprimir.");
    }
  }

  return (
    <Stack spacing={3}>
      <Typography variant="h4">Configuración de impresora</Typography>

      {/* WebUSB not supported */}
      {!detecting && !supported && (
        <Alert severity="warning">
          WebUSB no está disponible en este navegador. Usa Chrome o Edge en escritorio para imprimir tickets.
        </Alert>
      )}

      {/* Device section */}
      <Paper sx={{ p: 3, borderRadius: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h6">Impresora USB</Typography>

          {detecting ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              <CircularProgress size={18} />
              <Typography color="text.secondary" variant="body2">
                Detectando impresoras...
              </Typography>
            </Box>
          ) : (
            <Stack direction="row" alignItems="center" spacing={2} flexWrap="wrap">
              <UsbRoundedIcon sx={{ color: device ? "success.main" : "text.disabled" }} />
              <Box sx={{ flex: 1 }}>
                {device ? (
                  <>
                    <Typography fontWeight={700}>
                      {device.productName || device.manufacturerName || "Impresora USB"}
                    </Typography>
                    <Typography color="text.secondary" variant="caption">
                      {device.manufacturerName} · USB {device.usbVersionMajor}.{device.usbVersionMinor}
                    </Typography>
                  </>
                ) : (
                  <Typography color="text.secondary">Sin impresora autorizada</Typography>
                )}
              </Box>
              <Chip
                label={device ? "Conectada" : "Sin conectar"}
                size="small"
                sx={{
                  fontWeight: 700,
                  bgcolor: device ? "rgba(34,197,94,0.12)" : "rgba(148,163,184,0.12)",
                  color: device ? "success.main" : "text.secondary",
                }}
              />
            </Stack>
          )}

          {supported && (
            <Stack direction="row" spacing={1.5} flexWrap="wrap">
              <Button variant="outlined" size="small" startIcon={<UsbRoundedIcon />} onClick={handleConnect} disabled={status === "printing"}>
                {device ? "Cambiar impresora" : "Conectar impresora"}
              </Button>
              <Button
                variant="contained"
                size="small"
                startIcon={status === "printing" ? <CircularProgress size={14} color="inherit" /> : <PrintRoundedIcon />}
                onClick={handleTestPrint}
                disabled={!device || status === "printing"}
              >
                Imprimir ticket de prueba
              </Button>
            </Stack>
          )}

          {status === "error" && errorMessage && (
            <Alert severity="error" onClose={() => setStatus("idle")}>
              {errorMessage}
            </Alert>
          )}
        </Stack>
      </Paper>

      {/* Paper width */}
      <Paper sx={{ p: 3, borderRadius: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h6">Ancho de papel</Typography>
          <Typography color="text.secondary" variant="body2">
            Selecciona el ancho del rollo de tu impresora. 80 mm es el más común en impresoras térmicas de punto de venta.
          </Typography>
          <ToggleButtonGroup
            value={charWidth}
            exclusive
            onChange={(_, v) => {
              if (v !== null) setCharWidth(v as 32 | 42 | 48);
            }}
            size="small"
          >
            {PAPER_WIDTHS.map(({ label, value, mm }) => (
              <ToggleButton key={value} value={value} sx={{ px: 3, flexDirection: "column", gap: 0.25 }}>
                <Typography variant="body2" fontWeight={700}>
                  {label}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {mm}
                </Typography>
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Stack>
      </Paper>

      {/* Store info */}
      <Paper sx={{ p: 3, borderRadius: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h6">Datos de la tienda</Typography>
          <Typography color="text.secondary" variant="body2">
            Aparecen al pie de cada ticket impreso.
          </Typography>
          <Divider />
          <TextField
            label="Dirección"
            value={storeAddress}
            onChange={(e) => setStoreAddress(e.target.value)}
            placeholder="Calle 5 de Mayo 123, Col. Centro"
            fullWidth
            inputProps={{ maxLength: 80 }}
            helperText={`${storeAddress.length}/80 caracteres`}
          />
          <TextField
            label="Teléfono"
            value={storePhone}
            onChange={(e) => setStorePhone(e.target.value)}
            placeholder="555-123-4567"
            fullWidth
            inputProps={{ maxLength: 20 }}
          />
          <Typography variant="caption" color="text.secondary">
            Los cambios se guardan automáticamente en este navegador.
          </Typography>
        </Stack>
      </Paper>
    </Stack>
  );
}
