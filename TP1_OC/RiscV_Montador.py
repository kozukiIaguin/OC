from multiprocessing import Value
import operator
import re
import json
import os

OUTPUT_DIR = "outputs"
ASSEMBLY_PATH = "entrada.asm"

# Conjunto de instruções RISC-V
INSTRUCTIONS = {
    # Tipo I
    'lw':   {'opcode': 0b0000011, 'funct3': 0b010, 'type': 'I'},
    'addi': {'opcode': 0b0010011, 'funct3': 0b000, 'type': 'I'},
    'andi': {'opcode': 0b0010011, 'funct3': 0b111, 'type': 'I'},

    # Tipo S
    'sw':   {'opcode': 0b0100011, 'funct3': 0b010, 'type': 'S'},

    # Tipo R
    'sub':  {'opcode': 0b0110011, 'funct3': 0b000, 'funct7': 0b0100000, 'type': 'R'},
    'add':  {'opcode': 0b0110011, 'funct3': 0b000, 'funct7': 0b0000000, 'type': 'R'},
    'xor':  {'opcode': 0b0110011, 'funct3': 0b100, 'funct7': 0b0000000, 'type': 'R'},
    'srl':  {'opcode': 0b0110011, 'funct3': 0b101, 'funct7': 0b0000000, 'type': 'R'},
    'sll':  {'opcode': 0b0110011, 'funct3': 0b001, 'funct7': 0b0000000, 'type': 'R'},
    'or':   {'opcode': 0b0110011, 'funct3': 0b110, 'funct7': 0b0000000, 'type': 'R'},

    # Tipo B
    'beq':  {'opcode': 0b1100011, 'funct3': 0b000, 'type': 'B'}
}

# Mapeamento de registradores RISC-V
registers = {f'x{i}': i for i in range(32)}


def parse_register(reg_string):
    if not reg_string.startswith("x"):
        raise ValueError(f"Registrador {reg_string} inválido, não começa com x")
    try:
        reg_num = int(reg_string[1:])
    except ValueError:
        raise ValueError(f"Registrador inválido: {reg_string} número não aceito")
    if not 0 <= reg_num <= 31:
        raise ValueError(f"Registrador inválido (fora do intervalo x0 e x31)")
    return format(reg_num, '05b')


def build_r_type(instruction, operands):
    if len(operands) != 3:
        raise ValueError(f"Instrução {instruction} requer 3 operandos")
    rd, rs1, rs2 = operands
    rd_bin = parse_register(rd)
    rs1_bin = parse_register(rs1)
    rs2_bin = parse_register(rs2)
    instr_info = INSTRUCTIONS[instruction]
    return (
        (instr_info['funct7'] << 25) |
        (int(rs2_bin, 2) << 20) |
        (int(rs1_bin, 2) << 15) |
        (instr_info['funct3'] << 12) |
        (int(rd_bin, 2) << 7) |
        instr_info['opcode']
    )


def build_i_type(instruction, operands):
    if len(operands) != 3:
        raise ValueError(f"Instrução {instruction} requer 3 operandos")
    rd, rs1, imm = operands
    rd_bin = parse_register(rd)
    rs1_bin = parse_register(rs1)
    imm_val = int(imm, 0)
    imm_bin = format(imm_val & 0xFFF, '012b')
    instr_info = INSTRUCTIONS[instruction]
    return (
        (int(imm_bin, 2) << 20) |
        (int(rs1_bin, 2) << 15) |
        (instr_info['funct3'] << 12) |
        (int(rd_bin, 2) << 7) |
        instr_info['opcode']
    )


def build_s_type(instruction, operands):
    if len(operands) != 2:
        raise ValueError(f"Instrução {instruction} requer 2 operandos")
    rs2, offset_rs1 = operands
    match = re.match(r'(-?\d+)\((x\d+)\)', offset_rs1)
    if not match:
        raise ValueError(f"Formato inválido de offset(base): {offset_rs1}")
    offset, rs1 = match.groups()
    rs1_bin = parse_register(rs1)
    rs2_bin = parse_register(rs2)
    offset_val = int(offset, 0)
    imm_bin = format(offset_val & 0xFFF, '012b')
    imm_11_5 = imm_bin[:7]
    imm_4_0 = imm_bin[7:]
    instr_info = INSTRUCTIONS[instruction]
    return (
        (int(imm_11_5, 2) << 25) |
        (int(rs2_bin, 2) << 20) |
        (int(rs1_bin, 2) << 15) |
        (instr_info['funct3'] << 12) |
        (int(imm_4_0, 2) << 7) |
        instr_info['opcode']
    )


def build_b_type(instruction, operands):
    if len(operands) != 3:
        raise ValueError(f"Instrução {instruction} requer 3 operandos")
    rs1, rs2, imm = operands
    rs1_bin = parse_register(rs1)
    rs2_bin = parse_register(rs2)
    imm_val = int(imm, 0)
    imm_bin = format(imm_val & 0x1FFF, '013b')
    imm_12 = imm_bin[0]
    imm_10_5 = imm_bin[1:7]
    imm_4_1 = imm_bin[7:11]
    imm_11 = imm_bin[11]
    instr_info = INSTRUCTIONS[instruction]
    return (
        (int(imm_12, 2) << 31) |
        (int(imm_10_5, 2) << 25) |
        (int(rs2_bin, 2) << 20) |
        (int(rs1_bin, 2) << 15) |
        (instr_info['funct3'] << 12) |
        (int(imm_4_1, 2) << 8) |
        (int(imm_11, 2) << 7) |
        instr_info['opcode']
    )


def build_instruction(instruction, operands):
    instr_info = INSTRUCTIONS.get(instruction)
    if not instr_info:
        raise ValueError(f"Instrução {instruction} não suportada")
    instr_type = instr_info['type']
    if instr_type == 'R':
        return build_r_type(instruction, operands)
    elif instr_type == 'I':
        return build_i_type(instruction, operands)
    elif instr_type == 'S':
        return build_s_type(instruction, operands)
    elif instr_type == 'B':
        return build_b_type(instruction, operands)
    else:
        raise ValueError(f"Tipo {instr_type} não implementado ainda")


def riscv_assembler_file():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    output_path = os.path.join(OUTPUT_DIR, "output.txt")
    with open(ASSEMBLY_PATH, 'r') as asm_file, open(output_path, 'w') as out_file:
        for line_number, line in enumerate(asm_file, 1):
            line = line.strip()
            if not line or line.startswith("#"):  # Ignora comentários
                continue
            parts = re.split(r'[,\s()]+', line)
            instruction = parts[0]
            operands = parts[1:]
            try:
                instruction_bin = build_instruction(instruction, operands)
                out_file.write(f"{instruction_bin:032b}\n")
            except Exception as e:
                print(f"Erro na linha {line_number}: {line} -> {e}")

    print(f"Assemble finalizado. Arquivo gerado em: {output_path}")


def riscv_assembler_interactive():
    """Nova função interativa (com mesma estrutura do original)"""
    line_components = []
    binary_instructions = []  # Corrigido: acumula todas as instruções montadas

    print("\nModo interativo - Digite seu código assembly")
    print("(Linha vazia para terminar)\n")

    line_number = 1
    while True:
        line = input(f"{line_number:04d} > ").strip()
        if not line:  # Linha vazia encerra
            break
        if line.startswith('#'):  # Ignora comentários
            continue

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

        # Monta a instrução binária depois de identificar instrução e operandos
        inst_bin = build_instruction(components['instruction'], components['operands'])

        binary_instructions.append(inst_bin)  # Acumula saída final
        line_components.append(components)
        line_number += 1

    save_results(binary_instructions)  # Salva todas as instruções no arquivo




def save_results(instructions):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, 'result.txt')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(instructions))  # Junta tudo separando por quebra de linha

    print(f"Resultados salvos em {output_path}")



def save_lines_json(line_components, source):
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
            break

        elif choice == '2':
            riscv_assembler_interactive()
            break

        else:
            print("Opção inválida! Digite 0, 1 ou 2")
            break

if __name__ == "__main__":
    main_menu()


