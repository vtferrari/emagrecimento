# Scripts

Scripts de linha de comando do projeto.

## extract_cutting_report.py

Gera um relatório JSON com métricas de cutting a partir de:

- **ZIP** – Export do MyFitnessPal (deve conter CSVs de medidas, alimentação e exercícios)
- **PDF** – Relatório médico da Withings

### Uso

```bash
# Da raiz do projeto
python scripts/extract_cutting_report.py <arquivo.zip> <relatorio.pdf>
```

### Opções

| Opção        | Descrição                          | Padrão            |
|-------------|------------------------------------|-------------------|
| `--output`, `-o` | Arquivo JSON de saída              | `cutting_report.json` |

### Exemplos

```bash
python scripts/extract_cutting_report.py export.zip report.pdf
python scripts/extract_cutting_report.py export.zip report.pdf -o meu_relatorio.json
python scripts/extract_cutting_report.py export.zip report.pdf -o relatorio.json
```
