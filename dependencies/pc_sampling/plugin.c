#include <plugins/qemu-plugin.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;

static int pipe_fd = -1;
static uint64_t sample_interval = 10000;
static uint64_t random_offset = 0;
static uint64_t tb_count = 0;

static void vcpu_insn_exec(unsigned int vcpu_index, void *userdata)
{
    uint64_t insn_vaddr = (uint64_t)(uintptr_t)userdata;

    uint64_t count = __atomic_add_fetch(&tb_count, 1, __ATOMIC_RELAXED);

    if ((count + random_offset) % sample_interval == 0) {
        ssize_t ret = write(pipe_fd, &insn_vaddr, sizeof(uint64_t));
        (void)ret;
    }
}

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
    if (pipe_fd >= 0) {
        close(pipe_fd);
        pipe_fd = -1;
    }
}

QEMU_PLUGIN_EXPORT int qemu_plugin_install(qemu_plugin_id_t id,
                                           const qemu_info_t *info,
                                           int argc, char **argv)
{
    for (int i = 0; i < argc; i++) {
        char *opt = argv[i];
        if (strncmp(opt, "sample_interval=", 16) == 0) {
            sample_interval = strtoull(opt + 16, NULL, 0);
            if (sample_interval == 0)
                sample_interval = 1;
        } else if (strncmp(opt, "pipe_fd=", 8) == 0) {
            pipe_fd = atoi(opt + 8);
        }
    }

    if (pipe_fd < 0) {
        fprintf(stderr, "pc_sampler: pipe_fd argument required\n");
        return -1;
    }

    int flags = fcntl(pipe_fd, F_GETFL);
    if (flags >= 0)
        fcntl(pipe_fd, F_SETFL, flags | O_NONBLOCK);

    srand(time(NULL) ^ (getpid() << 16));
    random_offset = rand() % sample_interval;

    qemu_plugin_register_vcpu_tb_trans_cb(id, vcpu_tb_trans);
    qemu_plugin_register_atexit_cb(id, plugin_exit, NULL);

    fprintf(stderr, "pc_sampler: loaded. sample_interval=%" PRIu64 " pipe_fd=%d\n",
            sample_interval, pipe_fd);

    return 0;
}
