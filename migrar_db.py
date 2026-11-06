"""
Migração do banco: adiciona a tabela `atualizacoes_saldo` e a coluna
`automatica` em `movimentacoes_investimento`, sem apagar dados.

Uso:
    python migrar_db.py

Pode ser rodado mais de uma vez — ele verifica o que já existe antes de criar.
"""

import sqlite3
import os
import sys

DB_PATH = os.path.join("data", "financeiro.db")


def coluna_existe(cursor, tabela, coluna):
    cursor.execute(f"PRAGMA table_info({tabela})")
    return any(row[1] == coluna for row in cursor.fetchall())


def tabela_existe(cursor, tabela):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (tabela,),
    )
    return cursor.fetchone() is not None


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERRO: banco não encontrado em {DB_PATH}")
        print("Rode o app pelo menos uma vez para criar o banco, ou ajuste o caminho.")
        sys.exit(1)

    print(f"Conectando ao banco: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1) Coluna `automatica` em movimentacoes_investimento
        if not tabela_existe(cursor, "movimentacoes_investimento"):
            print("AVISO: tabela 'movimentacoes_investimento' não existe. Nada a fazer nela.")
        elif coluna_existe(cursor, "movimentacoes_investimento", "automatica"):
            print("OK: coluna 'automatica' já existe em movimentacoes_investimento.")
        else:
            print("Adicionando coluna 'automatica' em movimentacoes_investimento...")
            cursor.execute(
                "ALTER TABLE movimentacoes_investimento "
                "ADD COLUMN automatica BOOLEAN DEFAULT 0"
            )
            conn.commit()
            print("OK: coluna 'automatica' adicionada.")

        # 2) Tabela atualizacoes_saldo
        if tabela_existe(cursor, "atualizacoes_saldo"):
            print("OK: tabela 'atualizacoes_saldo' já existe.")
        else:
            print("Criando tabela 'atualizacoes_saldo'...")
            cursor.execute("""
                CREATE TABLE atualizacoes_saldo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ativo_id INTEGER NOT NULL,
                    data DATE NOT NULL,
                    saldo_informado FLOAT NOT NULL,
                    saldo_anterior FLOAT,
                    aportes_periodo FLOAT NOT NULL DEFAULT 0,
                    resgates_periodo FLOAT NOT NULL DEFAULT 0,
                    rendimento_liquido FLOAT,
                    rendimento_percentual FLOAT,
                    FOREIGN KEY (ativo_id) REFERENCES ativos (id)
                )
            """)
            conn.commit()
            print("OK: tabela 'atualizacoes_saldo' criada.")

        # 3) Diagnóstico final
        print("\n--- Diagnóstico ---")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tabelas = [r[0] for r in cursor.fetchall()]
        print("Tabelas no banco:", ", ".join(tabelas))

        if tabela_existe(cursor, "movimentacoes_investimento"):
            cursor.execute("PRAGMA table_info(movimentacoes_investimento)")
            colunas = [r[1] for r in cursor.fetchall()]
            print("Colunas de movimentacoes_investimento:", ", ".join(colunas))

        # contagem rápida para você ver que nada foi apagado
        for t in ["transacoes", "ativos", "movimentacoes_investimento", "recorrentes"]:
            if tabela_existe(cursor, t):
                cursor.execute(f"SELECT COUNT(*) FROM {t}")
                print(f"  {t}: {cursor.fetchone()[0]} registros")

        print("\nMigração concluída com sucesso.")
    except Exception as e:
        conn.rollback()
        print(f"\nERRO durante a migração: {e}")
        print("Nenhuma alteração parcial foi mantida (rollback feito).")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
