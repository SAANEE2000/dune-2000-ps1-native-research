#pragma once
#include "cpu_state.h"
#ifdef __cplusplus
extern "C" {
#endif
void dune_aot_missing(CPUState *cpu, unsigned address, const char *reason);
#ifdef __cplusplus
}
#endif
