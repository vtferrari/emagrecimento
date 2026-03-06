# Dashboard de Emagrecimento

Aplicação web para visualizar métricas de cutting a partir do export do MyFitnessPal (ZIP) e do relatório médico da Withings (PDF).

## Arquitetura (Clean Architecture)

```
src/emagrecimento/
├── domain/           # Entidades e value objects (sem dependências externas)
├── application/      # Use cases e interfaces (ports)
├── infrastructure/   # Adapters (ZIP, PDF, parsers)
└── container.py      # Composition root (injeção de dependências)
```

## Funcionalidades

- **Upload separado**: Carregue ZIP e PDF em áreas distintas
- **Botão Calcular**: Processa após selecionar os dois arquivos
- **Peso**: Gráfico com evolução, MA5, MA7 e variação
- **Alimentação**: Calorias, proteína, fibra, sódio e dias na meta
- **Exercícios**: Minutos, passos e calorias de exercício
- **Relatório Withings**: Métricas extraídas do PDF

## Como rodar

### 1. Instalar (editable para desenvolvimento)

```bash
pip install -e ".[dev]"
```

Ou apenas:

```bash
pip install -r requirements.txt
```

### 2. Iniciar o servidor web

```bash
python app.py
```

Acesse [http://127.0.0.1:5000](http://127.0.0.1:5000)

### 3. Ou usar CLI (script)

```bash
python scripts/extract_cutting_report.py arquivo.zip relatorio.pdf
python scripts/extract_cutting_report.py arquivo.zip relatorio.pdf -o meu_relatorio.json
```

Ver `scripts/README.md` para documentação completa.

## Testes (TDD)

```bash
pytest
pytest --cov=src/emagrecimento
```

## Estrutura do projeto

```
emagrecimento/
├── src/emagrecimento/     # Pacote principal (Clean Architecture)
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── container.py
├── scripts/               # Scripts de linha de comando
│   ├── extract_cutting_report.py
│   └── README.md
├── app.py                 # Web (Flask)
├── tests/
│   ├── unit/
│   └── integration/
├── templates/
├── static/
├── pyproject.toml
└── requirements.txt
```
