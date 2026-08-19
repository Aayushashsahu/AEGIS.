/**
 * Public, AEGIS-owned target used only for the bounded Mission 033
 * Scraper Studio validation. This is page content, not provider output.
 */
export const mission033TargetVersion = "v1";

export function mission033TargetHtml(): string {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AEGIS Verification Widget</title>
  </head>
  <body>
    <main data-mission="033" data-target-version="v1">
      <article class="product-card">
        <h1 class="product-title">AEGIS Verification Widget</h1>
        <p class="product-price" data-currency="USD">$599.00</p>
        <p class="product-availability">Available</p>
      </article>
    </main>
  </body>
</html>`;
}
