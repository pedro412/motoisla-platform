"use client";

import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import PersonRoundedIcon from "@mui/icons-material/PersonRounded";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import {
  AppBar,
  Box,
  Button,
  IconButton,
  Toolbar,
  Typography,
} from "@mui/material";

interface AppTopbarProps {
  title: string;
  onOpenMobileMenu: () => void;
}

export function AppTopbar({ title, onOpenMobileMenu }: AppTopbarProps) {
  return (
    <AppBar
      position="fixed"
      color="transparent"
      elevation={0}
      sx={{
        borderBottom: 1,
        borderColor: "divider",
        backdropFilter: "blur(4px)",
      }}
    >
      <Toolbar sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <IconButton
            edge="start"
            color="inherit"
            aria-label="abrir menú"
            onClick={onOpenMobileMenu}
            sx={{ display: { md: "none" } }}
          >
            <MenuRoundedIcon />
          </IconButton>
          <Typography component="h1" variant="h6" fontWeight={600}>
            {title}
          </Typography>
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Button startIcon={<PersonRoundedIcon />} variant="text" color="inherit">
            Perfil
          </Button>
          <Button startIcon={<LogoutRoundedIcon />} variant="outlined" color="inherit">
            Logout
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
