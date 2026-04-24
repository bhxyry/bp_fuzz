#include <plugins/qemu-plugin.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;

static FILE *out_fp = NULL;
static uint64_t sample_interval = 10000;
static uint64_t tb_count = 0;

static uint64_t *sample_buf = NULL;
static size_t buf_capacity = 8192;
static size_t buf_pos = 0;

static void flush_buffer(void)
{
    if (buf_pos == 0 || out_fp == NULL)
        return;

    size_t n = buf_pos > buf_capacity ? buf_capacity : buf_pos;
    fwrite(sample_buf, sizeof(uint64_t), n, out_fp);
    fflush(out_fp);
    buf_pos = 0;
}

static void vcpu_tb_exec(unsigned int vcpu_index, void *userdata)
{
    uint64_t vaddr = (uint64_t)(uintptr_t)userdata;

    uint64_t count = __atomic_add_fetch(&tb_count, 1, __ATOMIC_RELAXED);

    if (count % sample_interval == 0) {
        size_t pos = __atomic_fetch_add(&buf_pos, 1, __ATOMIC_RELAXED);
        if (pos < buf_capacity) {
            sample_buf[pos] = vaddr;
        }
        if (pos >= buf_capacity - 1) {
            flush_buffer();
        }
    }
}

static void vcpu_tb_trans(qemu_plugin_id_t id, struct qemu_plugin_tb *tb)
{
    uint64_t vaddr = qemu_plugin_tb_vaddr(tb);

    qemu_plugin_register_vcpu_tb_exec_cb(
        tb, vcpu_tb_exec, QEMU_PLUGIN_CB_NO_REGS,
        (void *)(uintptr_t)vaddr);
}

static void plugin_exit(qemu_plugin_id_t id, void *userdata)
{
    flush_buffer();
    if (out_fp) {
        fclose(out_fp);
        out_fp = NULL;
    }
    free(sample_buf);
    sample_buf = NULL;
}

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

    sample_buf = (uint64_t *)calloc(buf_capacity, sizeof(uint64_t));
    if (!sample_buf) {
        fprintf(stderr, "pc_sampler: failed to allocate sample buffer\n");
        return -1;
    }

    out_fp = fopen(out_path, "wb");
    if (!out_fp) {
        fprintf(stderr, "pc_sampler: cannot open output file %s\n", out_path);
        free(sample_buf);
        return -1;
    }

    qemu_plugin_register_vcpu_tb_trans_cb(id, vcpu_tb_trans);
    qemu_plugin_register_atexit_cb(id, plugin_exit, NULL);

    fprintf(stderr, "pc_sampler: loaded. sample_interval=%" PRIu64 " out_file=%s\n",
            sample_interval, out_path);

    return 0;
}
