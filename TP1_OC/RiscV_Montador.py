import re
import json
import os

OUTPUT_DIR = "outputs"

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

    os.makedirs(OUTPUT_DIR,exist_ok=True)

    #Pegar linha por linha do codigo e remover possiveis comentarios e vazios
    lines = [line.split('#')[0].strip() for line in assembly_code.split()]
    if lines:
    
        lines_path = os.path.join(OUTPUT_DIR,'lines.json')
        with open(lines_path,'w',encoding='utf-8') as f:
            json.dump(lines,f,ensure_ascii=False,indent=2)
    else:
        print("Nenhuma linha extraida")
        exit        

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

            try:
                instruction = INSTRUCTIONS[instr_name]
                binary = 0

                #Formato R(sub,xor,srl)
                if instruction['type'] == 'R':
                    rd = registers[parts[1]]
                    rs1 = registers[parts[2]]
                    rs2 = registers[parts[3]]
                    
                    binary = (
                        (instruction['funct7'] << 25) |
                        (rs2 << 20) |
                        (rs1 << 15) |
                        (instruction['funct3'] << 12) |
                        (rd << 7) |
                        instruction['opcode']
                )
                
                #Formato S(sw)
                elif instruction['type'] == 'S':
                    rs2 = registers[parts[1]]
                    rs1 = registers[parts[3]]
                    imm = int(parts[2])
                    imm_11_5 = (imm >> 5) & 0x7F #bits 11-5
                    imm_4_0 = imm & 0x1F # bits 4-0
                    binary = (
                        (imm_11_5 << 25) |
                        (rs2 << 20) |
                        (rs1 << 15) |
                        (instruction['funct3'] << 12) |
                        (imm_4_0 << 7) |
                        instruction['opcode']
                    )
                
                #Formato L(lw,addi)
                elif instruction['type'] == 'I':
                    rd = registers[parts[1]]
                    if instr_name == 'lw':
                        rs1 = registers[parts[3]]
                        imm = int(parts[2])
                    else:
                        rs1 = registers[parts[2]]
                        imm = int(parts[3])
                    
                    imm = imm & 0xFFF  # Garante 12 bits
                    binary = (
                        (imm << 20) |
                        (rs1 << 15) |
                        (instruction['funct3'] << 12) |
                        (rd << 7) |
                        instruction['opcode']
                    )

                 #Formato B(beq)
                elif instruction['type'] == 'B':
                    rs1 = registers[parts[1]]
                    rs2 = registers[parts[2]]
                    label = parts[3]
                    target_address = labels[label]
                    offset = target_address - current_address
                    
                    imm_12 = (offset >> 12) & 0x1
                    imm_10_5 = (offset >> 5) & 0x3F
                    imm_4_1 = (offset >> 1) & 0xF
                    imm_11 = (offset >> 11) & 0x1
                    
                    binary = (
                        (imm_12 << 31) |
                        (imm_10_5 << 25) |
                        (rs2 << 20) |
                        (rs1 << 15) |
                        (instruction['funct3'] << 12) |
                        (imm_4_1 << 8) |
                        (imm_11 << 7) |
                        instruction['opcode']
                    )
            
                machine_code.append(binary)
                current_address+=4
            except KeyError as e:
                print(f"Erro: instrucao ou registrador invalido - {line} ({str(e)})")
            except IndexError:
                print(f"Erro: Argumentos insuficientes - {line}")
            except:
                ValueError(f"Erro: valor invalido - {line}")

        return machine_code
                    
            
if __name__ == "__main__":
    assembly_program = """
        init:
            addi x1, x0, 10      # x1 = 10
            addi x2, x0, 0       # x2 = 0
        loop:
            lw x3, 0(x1)         # carrega mem[x1] em x3
            xor x4, x3, x2       # x4 = x3 XOR x2
            srl x5, x4, x2       # x5 = x4 >> x2 (lógico)
            sw x5, 4(x1)         # armazena x5 em mem[x1+4]
            sub x1, x1, x2       # x1 = x1 - x2
            beq x1, x0, end      # se x1 == 0, vai para end
            jal x0, loop         # volta para loop
        end:
            nop
        """

    machine_code = riscv_assembler(assembly_program)
    for i, code in enumerate(machine_code):
        print(f"0x{i*4:04X}: 0x{code:08X}")






