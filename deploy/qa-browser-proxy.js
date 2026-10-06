// Proxy de QA: backend local isolado, reproduz o encaminhamento feito pelo Caddy.
async (page) => {
  await page.route("**/api/v1/**", async route => {
    const requestUrl = new URL(route.request().url());
    const response = await route.fetch({ url: `http://127.0.0.1:8012${requestUrl.pathname}${requestUrl.search}` });
    await route.fulfill({ response });
  });
  await page.reload();
}
