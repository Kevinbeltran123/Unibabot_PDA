import { test, expect } from "@playwright/test";

test("register, logout, and login flow", async ({ page }) => {
  const email = `e2e-${Date.now()}@test.com`;
  const password = "playwright1234";

  await page.goto("/register");
  await expect(page.getByText("Crea tu cuenta")).toBeVisible();
  await page.getByLabel("Correo institucional").fill(email);
  await page.getByLabel("Contrasena").fill(password);
  await page.getByRole("button", { name: /crear cuenta/i }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("UnibaBot PDA")).toBeVisible();

  await page.getByRole("button", { name: /cerrar sesion/i }).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("Correo").fill(email);
  await page.getByLabel("Contrasena").fill(password);
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("dashboard shows empty state for new user", async ({ page }) => {
  const email = `e2e-empty-${Date.now()}@test.com`;
  await page.goto("/register");
  await page.getByLabel("Correo institucional").fill(email);
  await page.getByLabel("Contrasena").fill("playwright1234");
  await page.getByRole("button", { name: /crear cuenta/i }).click();
  await expect(page.getByText(/aun no has analizado/i)).toBeVisible();
  await expect(page.getByRole("link", { name: /analizar mi primer pda/i })).toBeVisible();
});
