// Respostas fictícias apenas para inspeção visual do onboarding; nenhum envio real.
async (page) => {
  for (const [rota, resposta] of Object.entries({
    disponibilidade: { ativo: true },
    solicitar: { desafio: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", reenviar_em: 60 },
    verificar: { prova: "prova-visual-sem-validade-real" },
    entrar: { tokens: null, onboarding_prova: "onboarding-visual-sem-validade-real" },
  })) {
    await page.route(`**/auth/whatsapp/${rota}`, route => route.fulfill({ json: resposta }));
  }
  await page.goto("http://127.0.0.1:3310/acesso-whatsapp");
  await page.setViewportSize({ width: 390, height: 844 });
}
