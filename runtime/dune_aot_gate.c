#include "dune_aot_gate.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
extern uint8_t psx_read_byte(uint32_t address);

void dune_aot_missing(CPUState *cpu, unsigned address, const char *reason) {
    /* No decode, execution, skip or success return on missing coverage. */
    fprintf(stderr, "DUNE_AOT_REQUIRED pc=0x%08X ra=0x%08X sp=0x%08X reason=%s\n",
            address, cpu->gpr[31], cpu->gpr[29], reason);
    FILE *receipt=fopen("dune_aot_gate_failure.json", "wb");
    if (receipt) {
        fprintf(receipt, "{\"status\":\"BLOCKED\",\"attempt_count\":1,"
                "\"interp_instruction_count\":0,\"pc\":\"0x%08X\","
                "\"ra\":\"0x%08X\",\"sp\":\"0x%08X\",\"reason\":\"%s\"}\n",
                address,cpu->gpr[31],cpu->gpr[29],reason);
        fclose(receipt);
    }
    fflush(stderr);
    /* Ignored local evidence: distinguish missing entry from a live-byte
       guard mismatch. Never use this snapshot as recompiler input. */
    FILE *snapshot=fopen("dune_aot_gate_ram.bin", "wb");
    if (snapshot) {
        unsigned char page[4096];
        for (unsigned offset=0;offset<0x200000;offset+=sizeof(page)) {
            for(unsigned i=0;i<sizeof(page);i++)page[i]=psx_read_byte(0x80000000u+offset+i);
            if(fwrite(page,1,sizeof(page),snapshot)!=sizeof(page))break;
        }
        fclose(snapshot);
    }
    exit(86);
}
