import sqlite3
import os

DB_PATH = os.path.join("data", "financeiro.db")

MAPEAMENTO = {
    "Cartao": "Cartão",
    "Debito Automatico": "Débito Automático",
    "PIX/Especie": "PIX/Espécie",
    "Fixo": "Fixo",
    "Extra": "Extra",
    "Investimento": "Investimento",
    "Receita": "Receita",
}

def main():
    if not os.path.exists(DB_PATH):
        print(f"ERRO: banco não encontrado em {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Antes da padronização:")
    cursor.execute("SELECT tipo, COUNT(*) FROM transacoes GROUP BY tipo")
    for tipo, qtd in cursor.fetchall():
        print(f"  {tipo}: {qtd}")

    for antigo, novo in MAPEAMENTO.items():
        if antigo != novo:
            cursor.execute("UPDATE transacoes SET tipo = ? WHERE tipo = ?", (novo, antigo))
            if cursor.rowcount > 0:
                print(f"Atualizados {cursor.rowcount} registros: '{antigo}' -> '{novo}'")

    conn.commit()

    print("\nDepois da padronização:")
    cursor.execute("SELECT tipo, COUNT(*) FROM transacoes GROUP BY tipo")
    for tipo, qtd in cursor.fetchall():
        print(f"  {tipo}: {qtd}")

    conn.close()
    print("\nConcluído.")

if __name__ == "__main__":
    main()
