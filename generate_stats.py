import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any

import requests

# 🔧 CONFIGURAÇÕES BÁSICAS
USERNAME = "BrunoDrezza"  # seu usuário GitHub
CURRENT_YEAR = datetime.now(timezone.utc).year  # sempre o ano atual
TOKEN = os.getenv("GH_TOKEN")  # vem do secret no GitHub Actions


def fetch_events(username: str, year: int, max_pages: int = 10, per_page: int = 100) -> List[Dict[str, Any]]:
    """
    Busca eventos públicos do usuário na API do GitHub e filtra somente os do ano especificado.
    A API só retorna os ~300 eventos mais recentes, então isso é um recorte aproximado do ano.
    """
    if not username:
        raise ValueError("USERNAME não pode ser vazio.")

    base_url = f"https://api.github.com/users/{username}/events/public"
    headers = {
        "Accept": "application/vnd.github+json",
    }

    # Usa token se disponível (melhor limite de rate)
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    session = requests.Session()
    events_for_year: List[Dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        resp = session.get(
            base_url,
            params={"page": page, "per_page": per_page},
            headers=headers,
            timeout=10,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Erro ao chamar GitHub API (status {resp.status_code}): {resp.text}"
            )

        page_events = resp.json()
        if not page_events:
            break  # acabou

        for event in page_events:
            created_at = event.get("created_at")
            if not created_at:
                continue

            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                continue

            if dt.year == year:
                events_for_year.append(event)
            elif dt.year < year:
                # Como a API vem ordenada do mais novo pro mais antigo,
                # se já chegou em ano menor, pode parar tudo.
                return events_for_year

    return events_for_year


def compute_stats(events: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Calcula estatísticas simples a partir da lista de eventos.
    """
    stats = {
        "total_events": 0,
        "push_events": 0,
        "commits": 0,
        "pull_requests_abertos": 0,
        "issues_abertas": 0,
        "repos_criados": 0,
    }

    for event in events:
        stats["total_events"] += 1
        ev_type = event.get("type")
        payload = event.get("payload", {}) or {}

        # Commits
        if ev_type == "PushEvent":
            stats["push_events"] += 1
            commits = payload.get("commits") or []
            stats["commits"] += len(commits)

        # PRs abertos
        if ev_type == "PullRequestEvent" and payload.get("action") == "opened":
            stats["pull_requests_abertos"] += 1

        # Issues abertas
        if ev_type == "IssuesEvent" and payload.get("action") == "opened":
            stats["issues_abertas"] += 1

        # Repositórios criados
        if ev_type == "CreateEvent" and payload.get("ref_type") == "repository":
            stats["repos_criados"] += 1

    return stats


def generate_svg(stats: Dict[str, int], username: str, year: int, output_path: str = "stats.svg") -> None:
    """
    Gera um cartão SVG simples com as estatísticas.
    """
    total = stats["total_events"]
    commits = stats["commits"]
    pushes = stats["push_events"]
    prs = stats["pull_requests_abertos"]
    issues = stats["issues_abertas"]
    repos = stats["repos_criados"]

    svg = f"""<svg width="480" height="190" viewBox="0 0 480 190" xmlns="http://www.w3.org/2000/svg">
  <style>
    .title {{
      font: 700 20px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
    .subtitle {{
      font: 400 12px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
    .label {{
      font: 500 13px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
    .value {{
      font: 600 13px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
  </style>

  <defs>
    <linearGradient id="cardGradient" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#f5f5f5" />
      <stop offset="100%" stop-color="#e0e0e0" />
    </linearGradient>
  </defs>

  <rect x="0.5" y="0.5" rx="12" ry="12" width="479" height="189" fill="url(#cardGradient)" stroke="#d0d0d0"/>

  <text x="24" y="40" class="title">GitHub Stats {year}</text>
  <text x="24" y="60" class="subtitle">@{username} • apenas eventos públicos</text>

  <g transform="translate(24, 85)">
    <text class="label" x="0" y="0">Eventos no ano:</text>
    <text class="value" x="160" y="0">{total}</text>

    <text class="label" x="0" y="22">Commits (PushEvent):</text>
    <text class="value" x="160" y="22">{commits}</text>

    <text class="label" x="0" y="44">Push events:</text>
    <text class="value" x="160" y="44">{pushes}</text>

    <text class="label" x="0" y="66">PRs abertos:</text>
    <text class="value" x="160" y="66">{prs}</text>

    <text class="label" x="0" y="88">Issues abertas:</text>
    <text class="value" x="160" y="88">{issues}</text>

    <text class="label" x="0" y="110">Repositórios criados:</text>
    <text class="value" x="160" y="110">{repos}</text>
  </g>

  <text x="24" y="176" class="subtitle">Dados baseados na API pública de eventos do GitHub (últimos ~300 eventos).</text>
</svg>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)


def main() -> None:
    if not TOKEN:
        print(
            "⚠️ AVISO: variá­vel de ambiente GH_TOKEN não definida. "
            "Localmente até funciona, mas no GitHub Actions você DEVE configurar o secret GH_TOKEN.",
            file=sys.stderr,
        )

    print(f"➡️ Buscando eventos de {USERNAME} para o ano de {CURRENT_YEAR}...")
    events = fetch_events(USERNAME, CURRENT_YEAR)
    print(f"✅ Eventos encontrados para {CURRENT_YEAR}: {len(events)}")

    stats = compute_stats(events)
    print(f"📊 Estatísticas calculadas: {stats}")

    generate_svg(stats, USERNAME, CURRENT_YEAR)
    print("🖼️ Arquivo 'stats.svg' gerado com sucesso.")


if __name__ == "__main__":
    main()
