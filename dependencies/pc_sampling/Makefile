GLIB_BASE := $(shell brew --prefix glib 2>/dev/null || echo /opt/homebrew/opt/glib)
GLIB_CFLAGS := -I$(GLIB_BASE)/include/glib-2.0 -I$(GLIB_BASE)/lib/glib-2.0/include
QEMU_INCLUDE := $(abspath ../qemu/include)

CC ?= clang
CFLAGS = -O2 -fPIC -fvisibility=hidden -std=c11

all: pc_sampling.so

pc_sampling.so: plugin.c
	$(CC) $(CFLAGS) $(GLIB_CFLAGS) -I$(QEMU_INCLUDE) -o $@ $< -shared -Wl,-undefined,dynamic_lookup

clean:
	rm -f pc_sampling.so
