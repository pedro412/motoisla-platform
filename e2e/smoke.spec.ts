import { expect, test } from "@playwright/test";

test("auth layout has no admin shell", async ({ page }) => {
  await page.goto("/login");

  await expect(page.getByRole("heading", { name: "MotoIsla Admin" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Entrar" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Perfil" })).toHaveCount(0);
});

test("admin route shows sidebar and topbar actions", async ({ page }) => {
  await page.goto("/dashboard");

  await expect(page.getByText("Dashboard").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Perfil" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Logout" })).toBeVisible();
});
