# Deploy no Homelab (Raspberry Pi 5 + Nginx Proxy Manager)

Guia para containerizar e publicar o Dashboard de Emagrecimento com Docker, usando Nginx Proxy Manager para SSL em `fit.vtferrari.space`.

## Pré-requisitos

- Docker e Docker Compose instalados no Raspberry Pi 5
- Nginx Proxy Manager rodando (geralmente em outro container ou no mesmo host)
- DNS: registro A ou CNAME apontando `fit.vtferrari.space` para o IP público do homelab
- Port forwarding: portas 80 e 443 do roteador apontando para o Pi

## Build e execução

```bash
cd /caminho/para/emagrecimento
docker compose build
docker compose up -d
```

O container expõe a porta 5000. O primeiro build pode levar alguns minutos (pandas, pypdf).

## Configuração no Nginx Proxy Manager

1. Acesse a interface do NPM (ex.: `http://<ip-do-pi>:81`).
2. **Proxy Hosts** → **Add Proxy Host**.
3. **Details**:
   - **Domain Names**: `fit.vtferrari.space`
   - **Scheme**: `http`
   - **Forward Hostname**: `emagrecimento` (se NPM e app estão na mesma rede Docker) ou IP do Pi (ex.: `192.168.1.x`)
   - **Forward Port**: `5000`
4. **SSL**:
   - Marque "SSL Certificate"
   - "Request a new SSL Certificate" (Let's Encrypt)
   - Aceite os termos e salve
5. **Advanced** (opcional, para uploads até 50 MB):
   - Adicione `client_max_body_size 50M;` se o NPM permitir custom nginx

## Rede Docker

- **NPM e emagrecimento no mesmo host**: Use o nome do serviço `emagrecimento` como Forward Hostname e coloque ambos na mesma rede Docker (ex.: `network_mode: host` ou rede custom compartilhada).
- **NPM em outro host**: Use o IP do Raspberry Pi como Forward Hostname e a porta 5000.

## Build para ARM64 a partir de x86

Se você buildar em máquina x86 para rodar no Pi:

```bash
docker buildx build --platform linux/arm64 -t emagrecimento:arm64 .
```

Depois copie a imagem para o Pi ou use um registry.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `PORT`   | `5000` | Porta em que o Gunicorn escuta |

Exemplo no `docker-compose.yml`:

```yaml
environment:
  - PORT=5000
```

## Considerações Raspberry Pi 5

- **Memória**: pandas pode usar bastante RAM em DataFrames grandes. Com 4–8 GB, o uso típico (ZIP/PDF de usuário) costuma ser tranquilo.
- **Build**: O primeiro build no Pi pode levar alguns minutos. Imagens em cache aceleram builds seguintes.
