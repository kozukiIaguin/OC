import re

#Conjunto 12 de instruções
INSTRUCTIONS = {
    'lw':   {'opcode': 0b0000011, 'funct3': 0b010, 'type': 'I'},
    'sw':   {'opcode': 0b0100011, 'funct3': 0b010, 'type': 'S'},
    'sub':  {'opcode': 0b0110011, 'funct3': 0b000, 'funct7': 0b0100000, 'type': 'R'},
    'xor':  {'opcode': 0b0110011, 'funct3': 0b100, 'funct7': 0b0000000, 'type': 'R'},
    'addi': {'opcode': 0b0010011, 'funct3': 0b000, 'type': 'I'},
    'srl':  {'opcode': 0b0110011, 'funct3': 0b101, 'funct7': 0b0000000, 'type': 'R'},
    'beq':  {'opcode': 0b1100011, 'funct3': 0b000, 'type': 'B'}
}

#Mapear os registradores do RiscV
registers = {f'x{i}': i for i in range(32)}

def riscv_assembler(assembly_code):

    machine_code = []
    labels = {}#Armazenar cada label da instrucao separado
    current_address = 0#Contador para o index de cada instrução

    #Pegar linha por linha do codigo e remover possiveis comentarios e vazios
    lines = [line.split('#')[0].strip() for line in assembly_code.split()]
    if lines:
        lines = [line for line in lines]


        #Encontrar e separar labels de cada instrucao, se tiver, ele armazena o endereço, se não avança 4 casas

        for line in lines:
            if ':' in line:
                label = line.split(':')[0].strip()
                labels[label] = current_address
            else:
                current_address +=4#4 bytes p a prox



        #Segunda passagem pela linha para fazer a montagem final
        current_address = 0
        for line in lines:
            if ':' in line:
                continue #Labels que ja foram processados

            #Dividir a instrucao em partes ['lw', 'x1', '4', 'x2']).
            parts = re.split(r'[\s,()]+', line.strip().lower())
            if parts:
                parts = [p for p in parts]
            else:
                continue
            instr_name = parts[0]

            #Codificar em binario
            







