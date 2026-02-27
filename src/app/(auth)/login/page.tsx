"use client";

import { Button, Paper, Stack, TextField, Typography } from "@mui/material";
import Link from "next/link";

export default function LoginPage() {
  return (
    <Paper elevation={3} sx={{ p: 4, width: "100%" }}>
      <Stack spacing={2.5}>
        <Typography variant="h5" component="h2" fontWeight={600}>
          Iniciar sesión
        </Typography>

        <TextField label="Correo electrónico" type="email" fullWidth />
        <TextField label="Contraseña" type="password" fullWidth />

        <Button variant="contained" size="large">
          Entrar
        </Button>

        <Button component={Link} href="/recuperar-cuenta" variant="text">
          ¿Olvidaste tu contraseña?
        </Button>
      </Stack>
    </Paper>
  );
}
