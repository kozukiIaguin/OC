from multiprocessing import Value
import operator
import re
import json
import os

OUTPUT_DIR = "outputs"
ASSEMBLY_PATH = "entrada.asm"

# Conjunto de instruções RISC-V
INSTRUCTIONS = {
    'lw':   {'opcode': 0b0000011, 'funct3': 0b010, 'type': 'I'},
    'sw':   {'opcode': 0b0100011, 'funct3': 0b010, 'type': 'S'},
    'sub':  {'opcode': 0b0110011, 'funct3': 0b000, 'funct7': 0b0100000, 'type': 'R'},
    'xor':  {'opcode': 0b0110011, 'funct3': 0b100, 'funct7': 0b0000000, 'type': 'R'},
    'addi': {'opcode': 0b0010011, 'funct3': 0b000, 'type': 'I'},
    'srl':  {'opcode': 0b0110011, 'funct3': 0b101, 'funct7': 0b0000000, 'type': 'R'},
    'beq':  {'opcode': 0b1100011, 'funct3': 0b000, 'type': 'B'}
}

# Mapeamento de registradores RISC-V
registers = {f'x{i}': i for i in range(32)}


def parse_register(reg_string):
    if not reg_string.startswith("x"):
        raise ValueError(f"Registrador {reg_string} invalido, nao comeca com x")
    try:
        reg_num = int(reg_string[1:])
    except ValueError:
        raise ValueError(f"Registrador invalido: {reg_string} numero nao aceito")
    if not 0 <= reg_num <= 31:
        raise ValueError(f"Registrador invalido (fora do intervalo x0 e x31)")

    reg_bin = format(reg_num,'05b')

    return reg_bin

def build_r_type(instruction,operands):
    #Verificar se tem o numero certo de operandos (regs)
    if len(operands) < 3:
        raise ValueError(f"Instrucao {instruction} requer 3 operandos")

    #Extrair registradores
    rd, rs1, rs2 = operands
    rd_bin = parse_register(rd)
    rs1_bin = parse_register(rs1)
    rs2_bin = parse_register(rs2)

    #Obter as informacoes dos campos de controle(funt e opcode)

    instr_info = INSTRUCTIONS[instruction]
    opcode = instr_info['opcode']
    funct3 = instr_info['funct3']
    funct7 = instr_info['funct7']

    instruction_bin = (
            (funct7 << 25) |
            (int(rs2_bin, 2) << 20) |
            (int(rs1_bin, 2) << 15) |
            (funct3 << 12) |
            (int(rd_bin, 2) << 7) |
            opcode
    )
    return instruction_bin

def riscv_assembler_file():  #alteração
    line_components = []  # Armazenar por cada linha

    try:
        with open(ASSEMBLY_PATH, 'r') as assembly_file:
            for line_number, line in enumerate(assembly_file, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Dicionário para armazenar os componentes desta linha
                components = {
                    'line_number': line_number,
                    'original': line,
                    'label': None,
                    'instruction': None,
                    'operands': [],

                }

                # Separar comentário
                code_part = line.split('#')[0].strip()


                # Processar tokens da linha
                tokens = [token.strip().rstrip(',') for token in code_part.split() if token.strip()]

                for i, token in enumerate(tokens):
                    if token.endswith(':'):
                        #  label
                        components['label'] = token[:-1]
                    elif i == 0 and components['label'] is None:
                        # instrução primeiro token sem ser o label
                        components['instruction'] = token
                    else:
                        # É um operando
                        components['operands'].append(token)

                line_components.append(components)

    except FileNotFoundError:
        print(f'Erro: Arquivo {ASSEMBLY_PATH} não encontrado')
        return None
    except Exception as e:
        print(f"Erro na leitura do arquivo: {e}")
        return None
        return save_to_json(line_components, ASSEMBLY_PATH)

def riscv_assembler_interactive():
    """Nova função interativa (com mesma estrutura do original)"""
    line_components = []
    print("\nModo interativo - Digite seu código assembly")
    print("(Linha vazia para terminar)\n")

    line_number = 1
    while True:
        line = input(f"{line_number:04d} > ").strip()
        if not line:  # Linha vazia encerra
            break
        if line.startswith('#'):  # Ignora comentários
            continue

        # Mesmo processamento do original
        components = {
            'line_number': line_number,
            'original': line,
            'label': None,
            'instruction': None,
            'operands': [],
        }

        code_part = line.split('#')[0].strip()
        tokens = [token.strip().rstrip(',') for token in code_part.split() if token.strip()]

        for i, token in enumerate(tokens):
            if token.endswith(':'):
                components['label'] = token[:-1]
            elif i == 0 and components['label'] is None:
                components['instruction'] = token
            else:
                components['operands'].append(token)

        line_components.append(components)
        line_number += 1

    return save_to_json(line_components, "entrada_interativa") if line_components else None

def save_to_json(line_components, source):
    """ (Adaptado para funcionar com ambos modos) """
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, 'lines_output.json')

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'source_file': source,
                'lines': line_components,
                'statistics': {
                    'total_lines': len(line_components),
                    'labels': sum(1 for line in line_components if line['label']),
                    'instructions': len(set(line['instruction']
                                            for line in line_components
                                            if line['instruction']))
                }
            }, f, ensure_ascii=False, indent=4)

        print(f"Arquivo processado. Saída em: {output_path}")
        return output_path
    except Exception as e:
        print(f"Erro ao salvar arquivo: {e}")
        return None

def main_menu():
    """Menu principal (igual ao seu original)"""
    global ASSEMBLY_PATH
    while True:
        print("\n" + "="*40)
        print(" MONTADOR RISC-V ".center(40))
        print("="*40)
        print("1. Processar arquivo")
        print("2. Modo interativo")
        print("0. Sair")

        choice = input("Escolha: ").strip()

        if choice == '0':
            print("Encerrando...")
            break

        elif choice == '1':
            ASSEMBLY_PATH = input("Caminho do arquivo [entrada.asm]: ").strip() or "entrada.asm"
            riscv_assembler_file()

        elif choice == '2':
            riscv_assembler_interactive()

        else:
            print("Opção inválida! Digite 0, 1 ou 2")

if __name__ == "__main__":
    main_menu()


