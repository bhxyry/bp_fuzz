#include <plugins/qemu-plugin.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <time.h>
#include <unistd.h>

QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;

static FILE *out_fp = NULL;
static uint64_t sample_interval = 10000;
static uint64_t random_offset = 0;
static uint64_t tb_count = 0;

static void vcpu_insn_exec(unsigned int vcpu_index, void *userdata)
{
    uint64_t insn_vaddr = (uint64_t)(uintptr_t)userdata;

    // 每执行一条指令，原子递增计数器
    uint64_t count = __atomic_add_fetch(&tb_count, 1, __ATOMIC_RELAXED);

    if ((count + random_offset) % sample_interval == 0) {
        fwrite(&insn_vaddr, sizeof(uint64_t), 1, out_fp);
        fflush(out_fp);
    }
}

//每当 QEMU 翻译一个新基本块时被调用
static void vcpu_tb_trans(qemu_plugin_id_t id, struct qemu_plugin_tb *tb)
{
    size_t n = qemu_plugin_tb_n_insns(tb);
    for (size_t i = 0; i < n; i++) {
        struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, i);
        uint64_t vaddr = qemu_plugin_insn_vaddr(insn);
        qemu_plugin_register_vcpu_insn_exec_cb(
            insn, vcpu_insn_exec, QEMU_PLUGIN_CB_NO_REGS,
            (void *)(uintptr_t)vaddr);
    }
}

static void plugin_exit(qemu_plugin_id_t id, void *userdata)
{
    if (out_fp) {
        fclose(out_fp);
        out_fp = NULL;
    }
}

//插件安装
QEMU_PLUGIN_EXPORT int qemu_plugin_install(qemu_plugin_id_t id,
                                           const qemu_info_t *info,
                                           int argc, char **argv)
{
    const char *out_path = "pc_samples.bin";

    for (int i = 0; i < argc; i++) {
        char *opt = argv[i];
        if (strncmp(opt, "sample_interval=", 16) == 0) {
            sample_interval = strtoull(opt + 16, NULL, 0);
            if (sample_interval == 0)
                sample_interval = 1;
        } else if (strncmp(opt, "out_file=", 9) == 0) {
            out_path = opt + 9;
        }
    }

    srand(time(NULL) ^ (getpid() << 16));
    random_offset = rand() % sample_interval;

    out_fp = fopen(out_path, "wb");
    if (!out_fp) {
        fprintf(stderr, "pc_sampler: cannot open output file %s\n", out_path);
        return -1;
    }

    qemu_plugin_register_vcpu_tb_trans_cb(id, vcpu_tb_trans);
    qemu_plugin_register_atexit_cb(id, plugin_exit, NULL);

    fprintf(stderr, "pc_sampler: loaded. sample_interval=%" PRIu64 " out_file=%s\n",
            sample_interval, out_path);

    return 0;
}
