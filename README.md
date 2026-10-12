# REPO ALFA

**Advanced Web Reverse Engineering, Deep Analysis, Reconstruction and Resilient Capture Framework.**

REPO ALFA é um framework modular para análise profunda, captura, mapeamento e reconstrução técnica de aplicações web. A proposta é combinar análise estática + dinâmica, navegador real, captura de rede, descoberta de rotas, fingerprinting, análise de bundles, armazenamento local, service workers, screenshots, validação e recuperação de falhas em um único pipeline reproduzível.

> Princípio central: uma falha isolada nunca deve derrubar toda a análise. O pipeline registra, preserva, tenta fallback, cria checkpoint e continua sempre que possível.

## Principais capacidades

- HTML bruto + DOM final renderizado
- CSS, fontes, imagens, SVG e assets
- JavaScript, bundles, chunks e referências a source maps publicados
- Fetch/XHR, GraphQL observado, WebSocket e EventSource
- Rotas SPA, links, navegação e estados observáveis
- localStorage, sessionStorage, IndexedDB e cookies acessíveis ao navegador
- Service Workers, manifestos e recursos PWA
- Fingerprinting de React, Next.js, Vue, Nuxt, Angular, Svelte, Astro, Remix, Vite e Webpack
- Screenshots desktop/mobile e validação visual
- Grafos de rotas, dependências e endpoints observados
- Checkpoints, resume, retries e Recovery Engine
- Relatórios JSON estruturados e preservação de evidências brutas
- Arquitetura extensível por analyzers/plugins

## Modos

```bash
repo-alfa scan https://example.com
repo-alfa capture https://example.com
repo-alfa map https://example.com
repo-alfa technologies https://example.com
repo-alfa deep https://example.com
repo-alfa forensic https://example.com
repo-alfa exhaustive https://example.com
repo-alfa reconstruct https://example.com
repo-alfa validate ./output/example.com
repo-alfa resume ./output/example.com
```

## Instalação

```bash
git clone https://github.com/alfa727337/REPO-ALFA.git
cd REPO-ALFA
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
playwright install chromium
```

## Exemplo rápido

```bash
repo-alfa deep https://example.com --output ./output
```

Saída típica:

```text
output/example.com/
├── html/
├── dom/
├── network/
├── javascript/
├── css/
├── assets/
├── screenshots/
├── storage/
├── service-workers/
├── routes/
├── reports/
├── checkpoints/
└── full-report.json
```

## Arquitetura

O motor é dividido em camadas independentes:

```text
Target
  ↓
Static Fetch
  ↓
Browser Capture (Playwright)
  ↓
Network + DOM + Storage + Assets
  ↓
Analyzers
  ↓
Recovery / Retry / Checkpoint
  ↓
Validation
  ↓
Structured Report
```

Cada módulo deve devolver resultado parcial mesmo quando encontra erros. O `RecoveryEngine` controla retries e registra falhas recuperáveis, e o `CheckpointStore` permite retomada.

## Segurança e uso autorizado

REPO ALFA foi desenhado para análise de aplicações públicas ou ambientes nos quais você possui autorização. Ele pode mapear e auditar superfícies observáveis, configurações, autenticação, sessões e APIs no contexto de testes autorizados, mas não existe para roubo de credenciais, sequestro de sessão ou acesso não autorizado a sistemas privados.

## Status

O projeto está em desenvolvimento ativo. O núcleo inicial já inclui CLI, fetch estático, captura dinâmica via Playwright, descoberta de links/endpoints observados, fingerprinting, checkpoints, recovery e relatório estruturado.
