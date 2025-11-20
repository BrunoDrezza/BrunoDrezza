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
    Gera um cartão SVG estiloso com as estatísticas.
    Visual mais parecido com o tema dark do GitHub.
    """
    total = stats["total_events"]
    commits = stats["commits"]
    pushes = stats["push_events"]
    prs = stats["pull_requests_abertos"]
    issues = stats["issues_abertas"]
    repos = stats["repos_criados"]

    def fmt(n: int) -> str:
        # formata com separador de milhar mais bonitinho (ex: 1 234)
        return f"{n:,}".replace(",", ".")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-labelledby="title desc">
  <title id="title">GitHub stats {year} de {username}</title>
  <desc id="desc">
    Estatísticas de eventos públicos do GitHub: total de eventos, commits, push events,
    pull requests abertos, issues abertas e repositórios criados em {year}.
  </desc>

  <style>
    .bg {{
      fill: #0d1117;
    }}
    .card {{
      fill: #161b22;
      stroke: #30363d;
      stroke-width: 1;
    }}
    .title {{
      font: 600 19px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      fill: #f0f6fc;
    }}
    .subtitle {{
      font: 400 12px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      fill: #8b949e;
    }}
    .label {{
      font: 400 13px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      fill: #c9d1d9;
    }}
    .value {{
      font: 600 13px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      fill: #f0f6fc;
    }}
    .accent {{
      fill: #58a6ff;
    }}
    .small {{
      font: 400 11px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      fill: #6e7681;
    }}
  </style>

  <!-- fundo geral -->
  <rect class="bg" x="0" y="0" width="495" height="195" rx="16" />

  <!-- card principal -->
  <rect class="card" x="8" y="8" width="479" height="179" rx="12" />

  <!-- linha decorativa -->
  <rect x="8" y="8" width="479" height="3" fill="#238636" />

  <!-- título -->
  <g transform="translate(26, 40)">
    <text class="title">GitHub Stats {year}</text>
    <text class="subtitle" y="18">@{username} · eventos públicos</text>
  </g>

  <!-- stats -->
  <g transform="translate(26, 88)">
    <!-- linha 1 -->
    <circle class="accent" cx="6" cy="-4" r="3" />
    <text class="label" x="18" y="0">Eventos no ano</text>
    <text class="value" x="230" y="0">{fmt(total)}</text>

    <!-- linha 2 -->
    <circle class="accent" cx="6" cy="20" r="3" />
    <text class="label" x="18" y="24">Commits (PushEvent)</text>
    <text class="value" x="230" y="24">{fmt(commits)}</text>

    <!-- linha 3 -->
    <circle class="accent" cx="6" cy="44" r="3" />
    <text class="label" x="18" y="48">Push events</text>
    <text class="value" x="230" y="48">{fmt(pushes)}</text>

    <!-- linha 4 -->
    <circle class="accent" cx="6" cy="68" r="3" />
    <text class="label" x="18" y="72">PRs abertos</text>
    <text class="value" x="230" y="72">{fmt(prs)}</text>

    <!-- linha 5 -->
    <circle class="accent" cx="6" cy="92" r="3" />
    <text class="label" x="18" y="96">Issues abertas</text>
    <text class="value" x="230" y="96">{fmt(issues)}</text>

    <!-- linha 6 -->
    <circle class="accent" cx="6" cy="116" r="3" />
    <text class="label" x="18" y="120">Repositórios criados</text>
    <text class="value" x="230" y="120">{fmt(repos)}</text>
  </g>

  <!-- rodapé -->
  <g transform="translate(26, 174)">
    <text class="small">
      Dados baseados na API pública de eventos do GitHub (últimos ~300 eventos).
    </text>
  </g>
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