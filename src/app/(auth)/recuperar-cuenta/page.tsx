"use client";

import { Button, Paper, Stack, TextField, Typography } from "@mui/material";
import Link from "next/link";

export default function RecoverAccountPage() {
  return (
    <Paper elevation={3} sx={{ p: 4, width: "100%" }}>
      <Stack spacing={2.5}>
        <Typography variant="h5" component="h2" fontWeight={600}>
          Recuperar cuenta
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Ingresa tu correo y te enviaremos instrucciones para recuperar el acceso.
        </Typography>

        <TextField label="Correo electrónico" type="email" fullWidth />

        <Button variant="contained" size="large">
          Enviar enlace
        </Button>

        <Button component={Link} href="/login" variant="text">
          Volver al login
        </Button>
      </Stack>
    </Paper>
  );
}
