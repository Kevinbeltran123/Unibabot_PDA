import { test, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";

const PDA_PATH = path.join(__dirname, "..", "..", "PDAs");

test("upload form accepts PDF and shows configuration", async ({ page }) => {
  const email = `e2e-upload-${Date.now()}@test.com`;
  await page.goto("/register");
  await page.getByLabel("Correo institucional").fill(email);
  await page.getByLabel("Contrasena").fill("playwright1234");
  await page.getByRole("button", { name: /crear cuenta/i }).click();

  await page.getByRole("link", { name: /analizar mi primer pda/i }).click();
  await expect(page).toHaveURL(/\/dashboard\/new$/);
  await expect(page.getByText(/arrastra un pdf/i)).toBeVisible();
  await expect(page.getByText(/rule-driven/i)).toBeVisible();
  await expect(page.getByText(/correcciones enriquecidas/i)).toBeVisible();
});

test.skip("end-to-end analysis (requires Ollama + real PDA)", async ({ page }) => {
  if (!fs.existsSync(PDA_PATH)) test.skip();
  const pdfs = fs.readdirSync(PDA_PATH).filter((f) => f.endsWith(".pdf"));
  if (pdfs.length === 0) test.skip();

  const email = `e2e-real-${Date.now()}@test.com`;
  await page.goto("/register");
  await page.getByLabel("Correo institucional").fill(email);
  await page.getByLabel("Contrasena").fill("playwright1234");
  await page.getByRole("button", { name: /crear cuenta/i }).click();

  await page.goto("/dashboard/new");
  await page.setInputFiles('input[type="file"]', path.join(PDA_PATH, pdfs[0]));
  await page.getByLabel(/codigo del curso/i).fill("22A14");
  await page.getByRole("button", { name: /iniciar analisis/i }).click();

  await expect(page).toHaveURL(/\/processing$/);
  await expect(page.getByText(/progreso global/i)).toBeVisible();

  await page.waitForURL(/\/dashboard\/analyses\/[^/]+$/, { timeout: 5 * 60_000 });
  await expect(page.getByText(/reporte de cumplimiento/i)).toBeVisible();
});
